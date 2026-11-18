"""Deterministic offline fitting with geometry-selection and blind-test splits."""
from __future__ import annotations
from collections import defaultdict
import itertools
import math
from ._io import digest, number
from .experiment import validate_dataset
from .model import FAMILIES, features, law_value
from .physics import RiderGeometry


def least_squares(matrix, values):
    """Column-scaled QR with two modified Gram-Schmidt passes; tiny dense fits.

    Deliberately no normal-equation inversion, NumPy dependency or arbitrary
    expression evaluation. Rank-deficient designs are rejected.
    """
    if not matrix or len(matrix) != len(values):
        raise ValueError("Invalid least-squares dimensions")
    n = len(matrix[0]);m = len(matrix)
    if not n or m < n or any(len(row) != n for row in matrix):
        raise ValueError("Underdetermined or ragged least-squares design")
    for row in matrix:
        for x in row:number(x)
    for y in values:number(y)
    scales = [math.sqrt(sum(row[j]**2 for row in matrix)) for j in range(n)]
    if any(s == 0 for s in scales):
        raise ValueError("Rank-deficient design")
    q = [];r = [[0.]*n for _ in range(n)]
    for j in range(n):
        col = [row[j]/scales[j] for row in matrix]
        for _ in range(2):
            for k in range(j):
                projection = sum(a*b for a,b in zip(q[k],col))
                r[k][j] += projection
                col = [a-projection*b for a,b in zip(col,q[k])]
        norm = math.sqrt(sum(a*a for a in col))
        if norm < 1e-12:
            raise ValueError("Rank-deficient design")
        r[j][j] = norm;q.append([a/norm for a in col])
    rhs = [sum(a*b for a,b in zip(column,values)) for column in q]
    coefficients = [0.]*n
    for j in range(n-1,-1,-1):
        coefficients[j] = (rhs[j]-sum(r[j][k]*coefficients[k] for k in range(j+1,n)))/r[j][j]
    return [c/s for c,s in zip(coefficients,scales)]


def error_stats(errors):
    if not errors:raise ValueError("An evaluation split is empty")
    return dict(count=len(errors),max_abs_w=max(map(abs,errors)),rmse_w=math.sqrt(sum(e*e for e in errors)/len(errors)),
                mean_abs_w=sum(map(abs,errors))/len(errors),bias_w=sum(errors)/len(errors))


def unique_observations(data):
    position_groups=defaultdict(list);lead_groups=defaultdict(list)
    for frame in data['frames']:
        if frame['purpose'] != 'calibration':continue
        for row in frame['observations']:
            position_groups[(row['profile_id'],row['speed_kph'],row['position'])].append(row)
            lead_groups[(row['profile_id'],row['speed_kph'])].append(row)
    positions=[];leads=[];repeat_checks=[]
    for key,rows in sorted(position_groups.items()):
        powers=[r['power_w'] for r in rows];span=max(powers)-min(powers)
        allowance=2*max(r['power_rounding_half_width_w'] for r in rows)+1e-8
        if len(rows)>1:repeat_checks.append(dict(profile_id=key[0],speed_kph=key[1],position=key[2],
            repeats=len(rows),span_w=span,rounding_allowance_w=allowance,pass_check=span<=allowance))
        row=dict(rows[0]);row['power_w']=sum(powers)/len(powers);positions.append(row)
    for _,rows in sorted(lead_groups.items()):
        values=[r['lead_power_w'] for r in rows]
        if max(values)-min(values)>.01000001:
            raise ValueError("Counterfactual lead power changes across rotations/context")
        row=dict(rows[0]);row['power_w']=sum(values)/len(values);row['position']=1;leads.append(row)
    return positions,leads,repeat_checks


def ftp_checks(data):
    result=[]
    for frame in data['frames']:
        if frame['purpose']!='ftp-invariance':continue
        matches=[f for f in data['frames'] if f['purpose']=='calibration' and f['batch_index']==frame['batch_index']
                 and f['order']==frame['order'] and f['speed_kph']==frame['speed_kph']]
        if len(matches)!=1:raise ValueError("FTP test lacks a unique matched baseline")
        baseline={r['profile_id']:r for r in matches[0]['observations']}
        for row in frame['observations']:
            old=baseline[row['profile_id']]
            difference=row['power_w']-old['power_w']
            allowance=row['power_rounding_half_width_w']+old['power_rounding_half_width_w']+1e-8
            lead_difference=row['lead_power_w']-old['lead_power_w']
            result.append(dict(profile_id=row['profile_id'],position=row['position'],normalization_ftp_w=row['normalization_ftp_w'],
                power_difference_w=difference,lead_difference_w=lead_difference,rounding_allowance_w=allowance,
                pass_check=abs(difference)<=allowance and abs(lead_difference)<=.01000001))
    return result


def fit_law(profiles, coefficients, index, family):
    matrix=[];values=[]
    for key in sorted(coefficients):
        p=profiles[key];value=coefficients[key][index]
        matrix.append(features(RiderGeometry(p['mass_kg'],p['height_cm']),family))
        values.append(math.log(value) if family=='power_law' else value)
    return dict(family=family,coefficients=least_squares(matrix,values))


def predict(cubic,linear,draft,row):
    rider=RiderGeometry(row['mass_kg'],row['height_cm']);v=row['speed_kph']/3.6
    a=law_value(cubic,rider);b=law_value(linear,rider)
    if not math.isfinite(a+b) or a<=0 or b<0:raise ValueError("Interpolation yielded nonphysical effective coefficients")
    return a*draft[row['position']-1]*v**3+b*v


def fit_dataset(data):
    profiles=validate_dataset(data);plan=data['plan']
    positions,leads,repeats=unique_observations(data)
    fit_speeds=set(plan['fit_speeds_kph']);blind_speeds=set(plan['blind_speeds_kph'])
    train_keys=sorted(k for k,p in profiles.items() if p['split']=='train')
    per_profile={}
    for key in train_keys:
        rows=[r for r in leads if r['profile_id']==key and r['speed_kph'] in fit_speeds]
        a,b=least_squares([[(r['speed_kph']/3.6)**3,r['speed_kph']/3.6] for r in rows],[r['power_w'] for r in rows])
        if a<=0 or b<0:raise ValueError("Cubic-plus-linear mechanics failed on a training profile")
        per_profile[key]=(a,b)
    draft=[1.]
    for position in range(2,6):
        rows=[r for r in positions if r['split']=='train' and r['speed_kph'] in fit_speeds and r['position']==position]
        xy=xx=0.
        for r in rows:
            a,b=per_profile[r['profile_id']];v=r['speed_kph']/3.6;x=a*v**3;y=r['power_w']-b*v
            xy+=x*y;xx+=x*x
        factor=xy/xx
        if not 0<factor<=1:raise ValueError("Constant aerodynamic drafting factor failed on training data")
        draft.append(factor)
    candidates=[]
    selection=[r for r in leads if r['split']=='selection' and r['speed_kph'] in fit_speeds]
    for cubic_family,linear_family in itertools.product(plan['body_candidates'],plan['linear_candidates']):
        cubic=fit_law(profiles,per_profile,0,cubic_family);linear=fit_law(profiles,per_profile,1,linear_family)
        errors=[predict(cubic,linear,draft,r)-r['power_w'] for r in selection]
        candidates.append(dict(cubic_law=cubic,linear_law=linear,selection=error_stats(errors),
                               parameter_count=FAMILIES[cubic_family]+FAMILIES[linear_family]))
    best_error=min(c['selection']['rmse_w'] for c in candidates)
    eligible=[c for c in candidates if c['selection']['rmse_w']<=best_error+plan['selection_tolerance_w']]
    selected=min(eligible,key=lambda c:(c['parameter_count'],c['selection']['rmse_w'],c['cubic_law']['family'],c['linear_law']['family']))
    cubic=selected['cubic_law'];linear=selected['linear_law']
    def blind(r):return r['split']=='test' or r['speed_kph'] in blind_speeds
    checks=[]
    for row in positions:
        predicted=predict(cubic,linear,draft,row)
        checks.append(dict(profile_id=row['profile_id'],split=row['split'],speed_kph=row['speed_kph'],position=row['position'],
            observed_w=row['power_w'],predicted_w=predicted,error_w=predicted-row['power_w'],blind=blind(row)))
    blind_positions=error_stats([r['error_w'] for r in checks if r['blind']])
    blind_lead=error_stats([predict(cubic,linear,draft,r)-r['power_w'] for r in leads if blind(r)])
    invariance=ftp_checks(data)
    monotone=all(a>=b-1e-6 for a,b in zip(draft,draft[1:]))
    accepted=(max(blind_positions['max_abs_w'],blind_lead['max_abs_w'])<=plan['acceptance_max_error_w']
              and all(r['pass_check'] for r in repeats+invariance) and monotone)
    context=data['frames'][0]['context']
    model=dict(schema_version=1,kind='effective-flat',model_id=plan['experiment_id'],
        context=context,cubic_law=cubic,linear_law=linear,draft_factors=draft,
        domain=dict(mass_kg=[min(profiles[k]['mass_kg'] for k in train_keys),max(profiles[k]['mass_kg'] for k in train_keys)],
                    height_cm=[min(profiles[k]['height_cm'] for k in train_keys),max(profiles[k]['height_cm'] for k in train_keys)],
                    speed_kph=[min(fit_speeds),max(fit_speeds)]),
        provenance=dict(source=data['source'],calculator_version=context['calculator_version'],plan_sha256=digest(plan),
                        dataset_sha256=digest(data),method='synthetic fixed-position flat IF readback; no source code copied'),
        validation=dict(accepted=accepted,criterion_max_abs_w=plan['acceptance_max_error_w'],
                        blind_positions=blind_positions,blind_lead=blind_lead,
                        repeatability_pass=all(r['pass_check'] for r in repeats),ftp_invariance_pass=all(r['pass_check'] for r in invariance),
                        draft_factors_monotone=monotone))
    report=dict(candidates=candidates,selected=selected,training_profile_coefficients={k:list(v) for k,v in per_profile.items()},
                checks=checks,repeats=repeats,ftp_invariance=invariance,lead_unique_count=len(leads),position_unique_count=len(positions),
                raw_calibration_count=sum(len(f['observations']) for f in data['frames'] if f['purpose']=='calibration'))
    return model,report


def markdown_report(model,report):
    v=model['validation'];context=model['context'];selected=report['selected']
    lines=['# Calibration audit: '+model['model_id'],'',
        '**Status: '+('PASS' if v['accepted'] else 'FAIL — not accepted for prediction')+'**','',
        'This audits agreement with a third-party calculator, **not actual in-game physics**. No personal team data was used.','',
        '## Reference context','',
        f"- Source: {model['provenance']['source']} · calculator v{context['calculator_version']}",
        f"- Route: {context['route_name']} ({context['route_signature']}), one lap.",
        f"- Manual efficiency: {context['efficiency']}; intensity: {context['intensity']}; team size: {context['team_size']}.",
        '- Equipment is not separately exposed by the web export; this is a pinned-context effective model.',
        f"- {report['raw_calibration_count']} static-position observations; {report['position_unique_count']} unique geometry/speed/position cells.",
        f"- {report['lead_unique_count']} unique counterfactual lead-power cells; repeated lead fields are deduplicated, not counted as independent evidence.",'',
        '## Predeclared separation','',
        'Nine body geometries train the model. Two different geometries select the interpolation family. Two further geometries and 40 km/h are held out from all fitting and family selection. Shared control geometries test repeatability under different neighboring riders.','',
        'Lead coefficients are fit at 25 and 50 km/h. Positional factors use only training geometries at those speeds. Candidates are ranked on the separate selection geometries; the simplest family within 0.05 W RMSE of the best is chosen. Blind tests are then evaluated once.','',
        '## Selected equations','',
        '```text','P(v, position) = alpha(mass,height) * draft[position] * v^3 + beta(mass,height) * v',
        'v in m/s, P in crank watts; position is one-based.',
        '```','',
        'Feature normalization: m = (mass_kg − 75)/25; h = (height_cm − 180)/25. Affine features are [1,m,h], quadratic [1,m,h,m²,mh,h²], mass-linear [1,m]. Power-law fits log(alpha) to [1, log(mass/75), log(height/180)].','',
        f"- Cubic law: `{model['cubic_law']}`",f"- Linear law: `{model['linear_law']}`",f"- Aero draft factors: `{model['draft_factors']}`",'',
        'Draft scales only the effective cubic term, not all watts. Neither fitted term separately identifies CdA, Crr, air density, drivetrain efficiency or equipment.','',
        '## Candidate selection (not the blind test)','',
        '| Cubic family | Linear family | Parameters | Selection RMSE W |','|---|---|---:|---:|']
    for c in report['candidates']:
        lines.append(f"| {c['cubic_law']['family']} | {c['linear_law']['family']} | {c['parameter_count']} | {c['selection']['rmse_w']:.6f} |")
    lines += ['', '## Blind-test results','', '| Readback | Cases | Maximum absolute error W | RMSE W |','|---|---:|---:|---:|']
    for label,key in [('Static positional watts','blind_positions'),('Counterfactual lead watts','blind_lead')]:
        s=v[key];lines.append(f"| {label} | {s['count']} | {s['max_abs_w']:.6f} | {s['rmse_w']:.6f} |")
    lines += ['',f"Predeclared acceptance limit: **{v['criterion_max_abs_w']:g} W maximum absolute error**. Static watts inherit approximately ±0.015 W rounding at the nominal 300 W FTP; counterfactual lead watts are reported to 0.01 W. These are source precision, not real-game uncertainty.",'',
        '| Position | Blind cases | Maximum absolute error W | RMSE W |','|---|---:|---:|---:|']
    for position in range(1,6):
        s=error_stats([r['error_w'] for r in report['checks'] if r['blind'] and r['position']==position])
        lines.append(f"| {position} | {s['count']} | {s['max_abs_w']:.6f} | {s['rmse_w']:.6f} |")
    lines += ['', '## Controls','',
        f"- Repeatability across different synthetic batches: {'PASS' if v['repeatability_pass'] else 'FAIL'} ({len(report['repeats'])} repeated cells).",
        f"- FTP 200/400 W normalization perturbation: {'PASS' if v['ftp_invariance_pass'] else 'FAIL'} ({len(report['ftp_invariance'])} rider comparisons against the matched 300 W baseline).",
        '- FTP is only used by the adapter to recover constant power from flat IF. It is not an input to the mechanical engine.',
        '- A fixed-position rider has constant power, so NP = P and P = flat_IF_percent * FTP / 100. The sole leader must independently agree with exported lead watts.',
        '- Route-adjusted wheel-power/NP fields are intentionally ignored.','',
        '## Coverage and limitations','',f"Observed interpolation envelope: `{model['domain']}`. Predictions outside it require an explicit extrapolation flag. An envelope is not a guarantee about every interior point.",'',
        'Only a five-rider, pinned-route, pinned-efficiency calculator context has been calibrated. No extrapolation to other team sizes, routes, bike choices, game versions, pack gaps, accelerations, gradients or physiological feasibility is validated. Numerical agreement at the test points does not uniquely identify the calculator’s internal formula.','',
        '## Reproduction identity','',f"- Experiment SHA-256: `{model['provenance']['plan_sha256']}`",f"- Dataset SHA-256: `{model['provenance']['dataset_sha256']}`",'',
        'Fit offline using the archived dataset. Do not replace failed blind tests with training examples; predeclare a new experiment before expanding the model.','']
    return '\n'.join(lines)

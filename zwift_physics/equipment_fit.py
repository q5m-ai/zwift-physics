"""Offline fit of complete steady-state chart observations; no HTTP client."""
import hashlib
import json
import math
from pathlib import Path

from ._io import load, number
from .engine import CyclingModel


def fit_reference(plan_path, observations_path):
    plan, obs = load(plan_path), load(observations_path)
    if (obs['plan_sha256'] != hashlib.sha256(Path(plan_path).read_bytes()).hexdigest()
            or obs['experiment'] != plan['experiment']):
        raise ValueError('Measurement design mismatch')
    rows = obs['measurements']; powers = obs['flat_power_w']; grades = obs['grade_pct']
    if ([r['frame'] for r in rows] != plan['frames'] + plan['frames'][:1] or rows[-1] != rows[0]
            or len(powers) < 5 or sorted(set(powers)) != powers or not all(120 <= number(p) <= 400 for p in powers)
            or grades != list(range(-3, 7)) or obs['grade_power_w'] != 250):
        raise ValueError('Missing coverage or repeatability control')
    profiles = []
    for r in rows[:-1]:
        flat, graded = [[number(v)/3.6 for v in r[k]] for k in ('flat_kph', 'graded_kph')]
        if (len(flat) != len(powers) or len(graded) != len(grades) or min(flat+graded) <= 0
                or sorted(set(flat)) != flat or r['mode'].lower() != ('road' if r['frame'] in ('zwift_aero','zwift_carbon') else 'tt')):
            raise ValueError('Unexpected speeds or riding mode')
        lo, hi = flat[0], flat[-1]
        a = (powers[-1]/hi - powers[0]/lo) / (hi**2-lo**2)
        b = powers[0]/lo - a*lo**2
        v = graded[-1]; g = grades[-1]/100
        c = ((250/v - a*v*v)*math.hypot(1,g)-b)/g
        model = CyclingModel(a,b,c)
        flat_err = max(abs(model.power_w(v)-p) for v,p in zip(flat[1:-1],powers[1:-1]))
        grade_err = max(abs(model.power_w(v,g/100)-250) for v,g in zip(graded,grades) if g not in (0,6))
        if max(flat_err,grade_err)>1 or b<=0:
            raise ValueError('Setup failed declared fit gate: '+r['frame'])
        profiles.append(dict(frame=r['frame'], wheels=plan['front_and_rear'], level=0, aero_socks=False,
                             reference_rider=dict(mass_kg=75,height_cm=180), status='exploratory',
                             coefficients=dict(aero=a,rolling_n=b,gravity_n=c,inertia_kg=None),
                             checks=dict(flat_max_error_w=flat_err,grade_max_error_w=grade_err)))
    return dict(source=plan['source'],experiment=plan['experiment'],profiles=profiles)


if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('observations',type=Path)
    args=p.parse_args();print(json.dumps(fit_reference(args.plan,args.observations),indent=2,allow_nan=False))

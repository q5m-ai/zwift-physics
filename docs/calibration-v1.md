# Calibration audit: gopher-flat-v1

**Status: PASS**

This audits agreement with a third-party calculator, **not actual in-game physics**. No personal team data was used.

## Reference context

- Source: https://zwiftgopher.com/TTT/ · calculator v1.39.1
- Collection window: 2026-11-18T15:13:58.425123+00:00 to 2026-11-18T15:19:33.123240+00:00.
- Route: Tempus Fugit (2128890027), one lap.
- Manual efficiency: 0; intensity: 0; team size: 5.
- Equipment is not separately exposed by the web export; this is a pinned-context effective model.
- 225 static-position observations; 195 unique geometry/speed/position cells.
- 39 unique counterfactual lead-power cells; repeated lead fields are deduplicated, not counted as independent evidence.

## Predeclared separation

Nine body geometries train the model. Two different geometries select the interpolation family. Two further geometries and 40 km/h are held out from all fitting and family selection. Shared control geometries test repeatability under different neighboring riders.

Lead coefficients are fit at 25 and 50 km/h. Positional factors use only training geometries at those speeds. Candidates are ranked on the separate selection geometries; the simplest family within 0.05 W RMSE of the best is chosen. Held-out tests are evaluated only after selection; no parameters are refit against them.

## Selected equations

```text
P(v, position) = alpha(mass,height) * draft[position] * v^3 + beta(mass,height) * v
v in m/s, P in crank watts; position is one-based.
```

Feature normalization: m = (mass_kg − 75)/25; h = (height_cm − 180)/25. Affine features are [1,m,h], quadratic [1,m,h,m²,mh,h²], mass-linear [1,m]. Power-law fits log(alpha) to [1, log(mass/75), log(height/180)].

- Cubic law: `{'family': 'quadratic', 'coefficients': [0.14812747776000001, 0.027591321600000003, 0.01682726399999999, -0.002607551999999973, 0.002513591999999981, -0.00039916800000004704]}`
- Linear law: `{'family': 'mass_linear', 'coefficients': [3.0335733333333343, 0.9083000000000002]}`
- Aero draft factors: `[1.0, 0.8326081711042577, 0.7768132380260022, 0.7271994844317398, 0.7271994844317398]`

Draft scales only the effective cubic term, not all watts. Neither fitted term separately identifies CdA, Crr, air density, drivetrain efficiency or equipment.

## Candidate selection (not the blind test)

| Cubic family | Linear family | Body-law coefficients | Selection RMSE W |
|---|---|---:|---:|
| power_law | mass_linear | 5 | 0.225264 |
| power_law | affine | 6 | 0.225264 |
| affine | mass_linear | 5 | 2.314012 |
| affine | affine | 6 | 2.314012 |
| quadratic | mass_linear | 8 | 0.113869 |
| quadratic | affine | 9 | 0.113869 |

## Blind-test results

| Readback | Cases | Maximum absolute error W | RMSE W |
|---|---:|---:|---:|
| Static positional watts | 85 | 0.253171 | 0.086406 |
| Counterfactual lead watts | 17 | 0.263171 | 0.104458 |

Predeclared acceptance limit: **1 W maximum absolute error**. Static watts inherit approximately ±0.015 W rounding at the nominal 300 W FTP; counterfactual lead watts are reported to 0.01 W. These are source precision, not real-game uncertainty.

| Position | Blind cases | Maximum absolute error W | RMSE W |
|---|---:|---:|---:|
| 1 | 17 | 0.253171 | 0.101393 |
| 2 | 17 | 0.226723 | 0.090351 |
| 3 | 17 | 0.197030 | 0.082136 |
| 4 | 17 | 0.194135 | 0.077908 |
| 5 | 17 | 0.194135 | 0.077908 |

## Controls

- Repeatability across different synthetic batches: PASS (30 repeated cells).
- FTP 200/400 W normalization perturbation: PASS (10 rider comparisons against the matched 300 W baseline).
- FTP is only used by the adapter to recover constant power from flat IF. It is not an input to the mechanical engine.
- A fixed-position rider has constant power, so NP = P and P = flat_IF_percent * FTP / 100. The sole leader must independently agree with exported lead watts.
- Route-adjusted wheel-power/NP fields are intentionally ignored.

## Coverage and limitations

Observed interpolation envelope: `{'mass_kg': [55, 95], 'height_cm': [160, 200], 'speed_kph': [25, 50]}`. Predictions outside it require an explicit extrapolation flag. An envelope is not a guarantee about every interior point.

Only a five-rider, pinned-route, pinned-efficiency calculator context has been calibrated. No extrapolation to other team sizes, routes, bike choices, game versions, pack gaps, accelerations, gradients or physiological feasibility is validated. Numerical agreement at the test points does not uniquely identify the calculator’s internal formula.

## Reproduction identity

- Experiment SHA-256: `fa23435409d09287de2c2ac2937e778abd8d07c1a4aca936a4e889fa92b571b6`
- Dataset SHA-256: `93e0869b8c27dd6077eac211120682b9819853f20320cfcf1c966bbfd9f976f5`

Fit offline using the archived dataset. Do not replace failed blind tests with training examples; predeclare a new experiment before expanding the model.

# Version 1: steady-flat, synthetic reference experiment

## Question

Can a small independent function of rider mass, height, flat speed and position
reproduce the calculator's effective steady-flat demand in a pinned context?
This does not ask whether the calculator reproduces actual Zwift physics.

## Scope held fixed

The design is in `experiments/gopher-flat-v1.json` and is hashed into the dataset.
The live preflight identified calculator v1.39.1. The full design pins that
version, Tempus Fugit route signature 2128890027, one lap, five riders, manual
team efficiency 0 and intensity 0. Every rider has normal effort and 100% power
adjustment. Bike/equipment details are not separately exposed in the web export.

The [API guide](https://zwiftgopher.com/api/dashboard.php) documents that draft
and automatic efficiency can depend on route, team strength and team size.
That is a reason to pin and record context, **not proof that every exported flat
field changes with all those settings**. Context effects need separate controlled
experiments; do not generalize this calibration to other contexts.

No real team inputs, rider IDs or accounts are used. FTP 300 W is a synthetic
normalization setting, not an assumed physiological capacity in the engine.

## Body and speed partitions

- Training: the 3×3 grid of 55/75/95 kg and 160/180/200 cm (nine geometries).
- Model selection: 65 kg / 170 cm and 85 kg / 190 cm.
- Unseen-geometry test: 60 kg / 195 cm and 90 kg / 165 cm.
- Coefficient-fit speeds: 25 and 50 km/h.
- Held-out speed: 40 km/h for all geometries.

A small preflight at 40 km/h checked the adapter/constant-position interpretation;
those values were not used to estimate coefficients or select a model family.
"Held out" here means excluded from coefficient fitting and family selection,
not a claim that the investigators had never seen any related pilot output.

Three batches of five fictional profiles cover these 13 geometries and repeat
two training controls under different surrounding riders. Each batch rotates
five ways. At each rotation, one rider pulls for 120 s and the other four have
0-second pulls; the formation is static. All three target speeds are sampled.

This yields 45 calculator snapshots / 225 position observations and 195 unique
geometry/speed/position cells. Each export also provides every rider's
counterfactual front watts; deduplicate these to 39 unique geometry/speed cells,
rather than counting repeated displayed numbers as independent tests.

## Which output is actually measured?

The selected-route export's `wheel_power` can be route-adjusted wheel NP. It is
not used as a flat power observation.

For a rider held at one position, power is constant, so NP = P. Recover:

```
flat watts = flat_if_percent * normalization_ftp_w / 100
```

The single front rider must independently agree with exported `pull_power`,
within the rounding intervals. Every response must retain the requested mass,
height, FTP, effort, power adjustment, order, pull duration, speed and context.

The export is rounded: flat IF has 0.01-percentage-point resolution, implying
approximately ±0.015 W at 300 W FTP; front watts are reported to 0.01 W. These are
measurement-format resolutions, not real-game uncertainty bounds.

## Additional falsification controls

- Compare the repeated geometry/speed/position cells in different batches. If
  differences exceed the combined rounding interval, do not average away a
  potential neighbor or context effect and call the positional model validated.
- In the final static formation at 40 km/h, change one follower's normalization
  FTP from 300 W to 200 W and then 400 W. All mechanical powers should remain
  unchanged within rounding, including those of the other four riders. This is
  a two-snapshot / ten-comparison control, not physiological calibration.

The design expects 168 HTTP requests, including the route form's POST → GET →
canonical GET redirects. A shared 200-request budget and ≥2 s spacing bound the
whole run across all three fresh anonymous sessions. There is no automatic retry.

## Independent model fitting

```
P_i,j(v) = alpha_i * d_j * v^3 + beta_i * v
```

1. Estimate each training geometry's alpha/beta from its two front-speed samples.
2. Fit shared position factors d₂…d₅ using only training geometries and fit
   speeds; d₁ is fixed at 1. Do not pre-impose d₄ = d₅.
3. Fit cubic-coefficient interpolation candidates: power law, affine and quadratic
   in body geometry. Fit linear-coefficient candidates: mass-linear and affine.
4. Compare the six candidates on the two selection geometries' front outputs at
   the fit speeds. Choose the fewest-parameter family within 0.05 W RMSE of best.
5. Evaluate, without refitting, the union of unseen geometries and held-out speed:
   85 unique positional cells and 17 front-power cells. These two readbacks
   overlap mechanistically; do not add them up as independent game validations.

The predeclared acceptance gate is **≤1 W maximum absolute error**, plus passing
repeatability, FTP-invariance and monotone/nonnegative drafting checks. A failed
model is written with `accepted: false` and the prediction loader refuses it.

Least squares uses column-scaled QR with re-orthogonalization. No third-party
numerics package, website source code, arbitrary expression evaluation, random
search or physiology fitting is involved.

## Interpretation

Alpha and beta are *effective* cubic and linear crank-power coefficients. Their
fit does not identify real CdA, Crr, air density, drivetrain efficiency or bike
mass separately. Gopher's internal formula is not uniquely determined by these
observations. A quadratic body-size interpolator may match it closely without
being its implementation.

The equation provides steady-flat mechanics, not acceleration, grade, road
surface, dynamic pack geometry, race-duration or performance-feasibility models.
The separate future physiology layer can consume mechanical watt traces; it
must not be allowed to change the mechanical watts merely to make a plan pass.

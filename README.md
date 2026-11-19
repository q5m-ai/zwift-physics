# zwift-physics

An independent, mechanics-first cycling model, calibrated through controlled
experiments with **fictional rider inputs**. Initial reference: the public
[ZwiftGopher TTT calculator](https://zwiftgopher.com/TTT/).

**Not affiliated with Zwift or ZwiftGopher. Not their source code.** Matching a
calculator is not validation against the actual game. Version 0.1 is a research
prototype for **steady flat power/speed and positional drafting**. Physiology and
race optimization are deliberately separate future work.

## Run the offline model

From this checkout, with Python 3.11+, no external dependencies or API keys:

```python
from zwift_physics import CyclingModel

# Illustrative rider + bike coefficients, not bare frame properties.
bike = CyclingModel(aero=0.16, rolling_n=3.0, gravity_n=800, inertia_kg=90)
v = bike.steady_speed_mps(watts=250, grade=0.05)  # 5% climb
print(round(v * 3.6, 1), 'km/h')
print(bike.power_w(speed_mps=10, draft_factor=0.8), 'W')  # only aero is reduced
```

The shared engine implements `P = A*d*v³ + B*r*v*cos(θ) + C*v*sin(θ) + D*v*a`, where `d` is the aero draft factor, `r` scales surface resistance, and `tan(θ)` is the grade. It also computes acceleration from power and current speed. The [five equipment profiles](zwift_physics/resources/profiles.json) are exploratory estimates at their specified fictional rider geometry; missing gravity or inertia means unmeasured, not zero. The original calibration API below retains its steady-flat envelope. Neither requires a live calculator.

## First calibration: measured, fitted, held out

| Item | Result |
|---|---|
| Reference | Gopher v1.39.1, Tempus Fugit, manual efficiency 0, five riders |
| Collection | 168 bounded HTTP requests; no account, API key or rider lookup |
| Geometry | 13 fictional profiles; nine train / two select / two test |
| Position data | 225 readings; 195 unique geometry/speed/position cells |
| Positional held-out error | **0.2532 W maximum**, 0.0864 W RMSE, 85 cases |
| Lead-power held-out error | **0.2632 W maximum**, 0.1045 W RMSE, 17 cases |
| Controls | Repeatability and FTP-normalization independence passed |
| Validated envelope | 55–95 kg, 160–200 cm, 25–50 km/h; positions 1–5 |

The source's nominal rounding is approximately ±0.015 W for positional readback.
The larger model errors include interpolation to new body geometries. Neither
number is an accuracy claim about real Zwift gameplay. The two readback sets
are not independent game validations.

- [Full calibration audit](docs/calibration-v1.md)
- [Predeclared protocol](docs/protocol.md)
- [Synthetic experiment design](experiments/gopher-flat-v1.json)
- [Curated numeric observations](data/gopher-flat-v1.json)
- [Accepted model coefficients](models/gopher-flat-v1.json)

## Use offline—no installation needed

Python 3.11+, standard library only. From the checkout:

```sh
python3 -m zwift_physics predict \
  --model models/gopher-flat-v1.json \
  --mass-kg 75 --height-cm 180 --speed-kph 45 --position 3

# Invert watts to steady flat speed instead:
python3 -m zwift_physics predict \
  --model models/gopher-flat-v1.json \
  --mass-kg 75 --height-cm 180 --watts 300 --position 1
```

```python
from zwift_physics import CalibrationModel, RiderGeometry

model = CalibrationModel.from_file("models/gopher-flat-v1.json")
rider = RiderGeometry(mass_kg=75, height_cm=180)
watts = model.power_watts(rider, speed_kph=45, position=3)  # about 262.66 W
speed = model.speed_kph(rider, watts=300, position=1)
```

Positions are one-based, **within the calibrated five-rider context**. Position 2
does not mean a different two-rider team. Outside-envelope predictions are
refused unless `--allow-extrapolation` / `allow_extrapolation=True` is explicitly
set; that flag does not invent unsupported draft positions or contexts.

## What is the engine?

At its core:

```text
P(v, position) = alpha(mass,height) * draft[position] * v³
                + beta(mass,height) * v
```

`v` is in m/s internally; the calibrated public API uses km/h. Output is crank
watts. The low-level `FlatCoefficients` API exposes the cubic and linear
components and a monotone watts-to-speed inverse.

The selected body-size interpolator is quadratic for `alpha` and mass-linear
for `beta`. See the audit and model JSON for coefficients and candidate-selection
results. Aero factors were **measured**, not imposed:

| Position | Cubic/aero factor |
|---:|---:|
| 1 | 1.000000 |
| 2 | 0.832608 |
| 3 | 0.776813 |
| 4 | 0.727199 |
| 5 | 0.727199 |

These multiply the cubic term, **not all power**. Fourth/fifth equality is an
observation in this reference context, not a universal in-game law.

## Refit and test, entirely offline

```sh
python3 -m unittest discover -s tests -v
python3 -m zwift_physics validate-data --data data/gopher-flat-v1.json
python3 -m zwift_physics fit \
  --data data/gopher-flat-v1.json \
  --model models/gopher-flat-v1.json \
  --report docs/calibration-v1.md
```

Fitting uses column-scaled QR, explicit train/selection/test partitions and a
predeclared 1 W maximum-error gate. Fits failing these validation gates are
written with `accepted: false` and cannot be loaded for prediction. Malformed
or incomplete datasets are rejected before writing a model. Input, model and
audit paths must be distinct files. Repeated runs are deterministic on the same
interpreter/platform; cross-version tests allow ordinary floating-point roundoff.
No held-out results are used to refit or select the model family.

Tests use a generated fake calculator plus the archived, sanitized reference.
They do not contact Gopher. GitHub Actions runs the offline suite on Python
3.11–3.14; nothing here publishes a package or deploys a service.

## Optional new HTTP experiments

Read the [collection policy](docs/collection-policy.md) first. **Gopher retains
JSON exports server-side**, even in an anonymous session. The runner accepts
only explicitly fictional profiles and never requests rider lookups.

```sh
# Default: zero network requests; show the design and budget.
python3 -m zwift_physics collect-gopher \
  --plan experiments/gopher-flat-v1.json

# Explicit live collection, into a NEW file. Never used by tests or CI.
python3 -m zwift_physics collect-gopher \
  --plan experiments/gopher-flat-v1.json \
  --output scratch/new-observations.json \
  --execute --acknowledge-server-retention \
  --max-requests 200 --interval-seconds 2
```

The current plan intentionally pins v1.39.1. If the site changes, collection stops:
inspect the new contract and declare a new experiment rather than overwriting
history or weakening checks. The adapter is serial and bounded, counts redirects,
stops on denials/rate limits/uncertain writes, never retries, and writes only
allowlisted numeric observations. It discards raw exports, generated links,
identities, cookies and physiological outputs.

## Boundaries and next work

- Effective coefficients do not uniquely identify CdA, Crr, air density,
  drivetrain losses, bike mass or Gopher's internal implementation.
- One calculator version and context have been calibrated. Equipment and pack
  dynamics are not experimentally identified here.
- No hills, acceleration, surfaces, gaps, fatigue, CP, W′, physiological
  feasibility or finish-time prediction is claimed.
- FTP appears **only in the measurement adapter** to decode `flat_if`; it is not
  a mechanical-model parameter. A separate physiology layer may later consume
  power traces without changing the mechanical demand.

See [the roadmap](docs/roadmap.md) and [contribution guidelines](CONTRIBUTING.md).

## License and data provenance

Authored code and documentation: [MIT](LICENSE). Numeric reference observations
are factual outputs of our synthetic experiments, with explicit provenance;
no licence is claimed over ZwiftGopher's software, branding or third-party
material. See [data notes](data/README.md). No personal team data, raw exports,
website source, credentials or transcripts are included.

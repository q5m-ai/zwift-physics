# zwift-physics

An independent, mechanics-first cycling model, calibrated through controlled
experiments with **fictional rider inputs**. Initial reference: the public
[ZwiftGopher TTT calculator](https://zwiftgopher.com/TTT/).

**Not affiliated with Zwift or ZwiftGopher. Not their source code.** Matching a
calculator is not validation against the actual game. This project starts with
steady flat power/speed and positional drafting. Physiology and race optimization
are deliberately separate future work.

## First milestone

- Transparent effective flat mechanics: `P = alpha * draft * v³ + beta * v`.
- Body-size interpolation rather than five named riders baked into the model.
- Explicit calculator context: route, manual efficiency, team size and version.
- A bounded, opt-in HTTP experiment runner; no accounts or rider lookups.
- Separate training, model-selection and blind-test cases; offline tests.
- Public-safe numeric observations, provenance and reproducible fitting.

The project is being prepared locally. No GitHub repository or package has yet
been published. Calibration results will be documented after the first controlled
collection; do not mistake synthetic unit-test fixtures for live measurements.

## Development

Python 3.11+; standard library at runtime and during calibration. No installation
is needed when running from the checkout:

```sh
python3 -m unittest discover -s tests -v
python3 -m zwift_physics --help
```

Network collection is never part of a test or a normal prediction. See the
experiment protocol and collection policy under `docs/` before running it.

## Scope and licensing

Authored code and documentation: MIT. Numerical reference observations are
factual outputs of our synthetic experiments, with explicit source provenance;
no license is claimed over ZwiftGopher's software, branding or third-party
material. No website source, raw exports, personal rider data or credentials
belong in this repository.

A calibrated cubic/linear decomposition does **not** separately identify real
CdA, rolling resistance, air density, drivetrain losses or equipment. No hills,
acceleration, surfaces, equipment comparison, pack gaps, fatigue, CP, W′,
physiological feasibility or finish-time prediction are claimed in this milestone.

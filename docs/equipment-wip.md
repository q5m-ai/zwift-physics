# Equipment dataset checkpoint

Continue on `feature/offline-physics` (PR #1). The deliverable is an offline, source-labeled equipment coefficient dataset, not just a list of bike names.

- Current coverage: 11 exact setups across 10 unique frames. Eight are Speed Lab stage-0 frames on CADEX 42 wheels, with effective aero, rolling and climbing coefficients. No inertia is inferred from those steady curves. Three flat-only Gopher setups cover two other frames. Two earlier pilot setups are excluded because their original calculator context and observations are unavailable.
- Start with `experiments/speedlab-reference-v1.json`, `data/speedlab-reference-v1.json`, and `zwift_physics/equipment_fit.py`. The README gives the offline rebuild and lookup commands. Run `python3 -m unittest discover -s tests -q`.
- The earlier inventory of 167 frames and 90 wheelsets, and the proposed coverage manifest, are available on the separate local `work/solo-tt-mechanics` branch at `2e5aefd`. It is not necessary to merge that branch to read its files. Do not count inventory entries as fitted profiles.
- Next: reconcile unmeasured frame IDs with compatible reference wheels, then predeclare a new bounded experiment (or use a documented, reusable bulk data source). Preserve source attribution, unchanged controls and evaluation checks. Maintain separate rows for measured setups; no silent defaults for missing data. See `docs/collection-policy.md`.

# Numeric reference observations

`gopher-flat-v1.json` is a **curated numeric extract**, not a raw website export.
The observation inputs are intentionally fictional experimental geometries, not
a team roster or anonymized copies of real riders.

It contains:

- The predeclared synthetic design and its SHA-256.
- Collection timestamps, completion status and HTTP request count.
- 45 static-formation snapshots / 225 positional observations.
- Two normalization-FTP perturbation snapshots / ten rider comparisons.
- Observed source version, route and explicit calculator settings.
- Per-observation mass, height, position, target speed, derived flat watts,
  counterfactual lead watts, normalization FTP, flat IF and rounding interval.

It deliberately excludes raw JSON/HTML, source rider identifiers, rider names,
server session identifiers, cookies, credentials, generated links, physiological
estimates, race predictions, account data and logs. Synthetic geometry labels
are experiment identifiers, not real athlete identifiers. The strict validator
rejects extra fields rather than letting these enter a release artifact.

The measurement is `flat_if_percent * normalization_ftp_w / 100` for a fixed
position; the leader provides an independent readback check. Exported route-
adjusted wheel NP is not fitted as flat power. Source precision is disclosed in
the audit. These measurements do not independently verify actual game physics.

The numeric observations are factual results of our own synthetic experiments.
The authored collection/fitting code and documentation are MIT-licensed; no
copyright claim over mathematical facts or licence over the third-party service
or its implementation is implied. Preserve source attribution, calibration
context and limitations when reusing the dataset. See
[collection and reuse boundaries](../docs/collection-policy.md).

Do not refresh this file in place from a changed service. Add a new experiment
and keep its validation split separate. A user's future real-rider validation
files must stay outside this public dataset, under an ignored private path.

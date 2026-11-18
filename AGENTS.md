# zwift-physics

Independent, mechanics-first modeling from controlled synthetic experiments.
This is not Zwift's game engine or ZwiftGopher's implementation.

- Keep physiology (FTP/CP/W′, fatigue, recovery, pacing optimization) out of the
  mechanics core. FTP appears only as a normalization input in the Gopher
  measurement adapter; it is not a mechanical model parameter.
- No real names, rider IDs, team inputs, accounts, cookies, keys, raw exports,
  generated share links, private reports or transcripts in Git or fixtures.
- Use fictional profiles and strict allowlisted numeric observations. Network
  collection must be opt-in, bounded and serial; stop on 401/403/429, service
  errors, schema changes or uncertain writes. No retry, key rotation or bypass.
- Pin and verify the calculator version/context, including route, manual team
  efficiency, team size and intensity. A route-conditioned calculator draft
  factor is not a universal game constant.
- Preserve training/model-selection/blind-test partitions. Never silently train
  on a failed holdout. Show errors, coverage, source rounding and extrapolation.
- All tests must run offline: `python3 -m unittest discover -s tests -v`.
- Keep runtime/fitting standard-library-only. Do not install global tools or
  create credentials without explicit approval.
- Make focused validated local commits. Publishing needs the user's approval
  for the exact GitHub owner/repository. No merge, deploy or package release is
  implied by permission to develop.

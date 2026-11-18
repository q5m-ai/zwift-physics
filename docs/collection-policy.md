# Collection, privacy and reuse boundaries

## Reference material inspected

- [Public calculator](https://zwiftgopher.com/TTT/) and its browser-delivered
  JavaScript: used to learn ordinary form/JSON-export interactions, not copied
  into this repository or treated as access to server-side physics source.
- [API guide](https://zwiftgopher.com/api/dashboard.php): describes a keyed
  official API, manual rider inputs, `evaluate_only`, context and usage limits.
  No API key was created or accessed for this milestone.
- [Privacy policy](https://zwiftgopher.com/TTT/privacy): says JSON exports retain
  a copy of the plan server-side: the last export per team/race, deleted after
  two years. Anonymous does not mean unlogged or unretained. Use fictional
  profiles only.
- `/robots.txt` returned 404 during preflight. Its absence is not a license or
  authorization to perform unlimited automated requests.

No explicit permission to copy the private implementation is inferred. Numerical
input/output observations and independently authored equations are the basis of
this project. We found no public core-source licence; do not present this as a
fork, official implementation or legal determination about every jurisdiction.
Review current terms before publishing or enlarging a collection campaign.

## Live-adapter rules

- Offline by default. Both `--execute` and `--acknowledge-server-retention` are
  required to send a bounded experiment.
- Only manually entered, explicitly fictional profiles; no Zwift IDs or profile
  lookups, authentication, saved squads or existing browser cookies.
- New in-memory anonymous sessions; refuse any unexpectedly nonempty session.
- Requests are serial, ≥2 seconds apart, with an explicit shared budget. Redirect
  GETs count too. No concurrency, remote optimization or polling loop.
- The course form's observed 302 response is followed as a **GET**, never a
  replayed POST. Unexpected destinations, 307/308 write replays and cross-origin
  redirects are refused.
- Any 401, 403, 429, service error, timeout or schema/context mismatch stops the
  run. No automatic retries, key rotation, proxy, alternate transport or attempt
  to bypass a denial. Investigate the failure before starting a new experiment.
- No image/share-link action is invoked. A normal JSON export can nevertheless
  contain a generated link and is itself retained by the service. All such
  fields are discarded in memory; only an allowlist of numeric observations and
  public context is written.
- A failed run retains a clearly marked incomplete checkpoint. Incomplete data
  cannot fit a release model; existing observation files are never overwritten
  by the live collector. There is no blind session-resume feature.

## Public artifacts

Permitted: authored code and docs, fictional design inputs, strict numeric
observations, model coefficients, error summaries and tests.

Excluded: real team inputs, names/IDs, cookies, credentials, raw exports, generated
share links, downloaded website scripts, request/response dumps, browser state,
transcripts and logs. `scratch/` and `private/` are ignored, not encrypted.

Code/docs are MIT-licensed. We make no grant over third-party code, trademarks,
services or rights we do not own. The numerical dataset records factual results
of our own synthetic experiments; attribution and scope travel with it. A small
UI-based campaign is not a blanket licence for bulk extraction or redistribution
of other third-party material. Prefer an approved official API integration for
larger campaigns, with credentials kept outside source control and chat.

## Next collection changes

Any source version, route, equipment, group-size or efficiency change starts a
new experiment ID and archive. Do not silently refresh an existing model from a
changing service. Before publication, review the staged file list and dataset
schema, choose the GitHub owner, and obtain explicit publication approval.

# Contributing

1. Read `AGENTS.md`, `docs/protocol.md` and `docs/collection-policy.md`.
2. Keep mechanics independent of physiology. Add no rider identities or real
   team data, even to tests, examples, commit messages or old revisions.
3. Use generated synthetic tests. Never make service requests in tests or CI.
4. Add tests for new equations, units, invalid inputs and calibration boundaries.
5. Predeclare new experiments before collecting data: context, parameter ranges,
   training/selection/held-out partitions, request budget and acceptance limits.
6. Do not tune against a failing held-out set and still describe it as held out.
   Publish the failed attempt in the audit and reserve fresh validation cases.
7. Every public observation must pass the allowlisted schema and provenance
   checks. Never add raw website exports, share links, cookies, tokens or logs.
8. Run `python3 -m unittest discover -s tests -v`. Refit archived observations
   offline; compare numerical results with floating-point tolerances.
9. Keep commits focused. A release of a new model requires a reproducible audit,
   an explicit accepted flag and documented scope; no automatic network refresh.

The HTTP adapter follows an observed public website interface, not a stable
licensed backend specification. Keep collection deliberately small and stop
rather than working around a denial or rate limit. Prefer an authorized official
API integration for larger future campaigns; do not create or obtain a key
without the relevant approval, and never put it in Git or chat.

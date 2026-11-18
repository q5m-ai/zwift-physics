# Roadmap: mechanics first, physiology downstream

## Completed foundation

- Independent cubic/linear steady-flat engine, explicit units and inverse speed.
- Body-size interpolation selected independently of held-out validation cases.
- Synthetic first-through-fifth positional calibration, including zero pulls.
- Bounded opt-in collection, context/provenance checks and offline reproducibility.
- No rider identities or physiological assumptions in the mechanical API.

## Next mechanical experiments

1. **Context dependence.** Predeclare tests across manual efficiency settings,
   team sizes and selected routes. Determine which flat readbacks actually
   respond; do not infer dependence merely from a route-level API description.
2. **Broader geometry/speed envelope.** Add fresh held-out geometries and speeds
   before extending interpolation or claiming a more exact body-size law.
3. **Actual-game validation.** Treat observations from real Zwift rides as a
   separate reference layer, not confirmation automatically inherited from
   matching Gopher. Keep personal rider/ride files private; publish only an
   explicitly approved non-sensitive benchmark extract.
4. **Gradient and acceleration.** Add force/energy equations with independently
   identified parameters and tests. Aggregate route time and route-adjusted NP
   do not uniquely identify instantaneous CdA, rolling resistance or inertia.
5. **Surface, bike and formation effects.** Do not invent coefficients where the
   calculator interface or observations do not isolate the relevant variable.

## Then: an optional physiological layer

A separate module can consume rider-specific mechanical power traces and model
CP/W′, recovery, NP/IF and fatigue. It must:

- distinguish measured rider parameters from assumptions;
- preserve the mechanical watts independently of whether a rider can sustain them;
- handle uncertainty and individual limits, not only a team-average score;
- keep private rider profiles and results outside the public benchmark;
- expose recovery-law alternatives and tests rather than present one law as fact.

Pull scheduling and race optimization belong above both layers. They are not
required to calibrate mechanical demand, and are not part of this first release.

# Feature

**You own the design.** New or changed behavior, built from a named data shape.

1. Run `how` over the affected subsystem, including merged or in-flight work.
2. Name the data shape and its organizing structure (**Model the domain**)
   before writing logic. If the code crosses a module boundary, run
   `architect`. If several valid shapes have real cost differences, run `arena`.
3. Write the throughput checkpoint as four todos; mark one that does not apply
   `n/a: <reason>` instead of dropping it:
   - **Blocking first steps.** Gates that run before any fan-out.
   - **Independent workstreams.** Disjoint files, services or layers parallelize;
     shared writes serialize.
   - **Shared mutable state.** Split the target before serializing access.
   - **Smallest safe decomposition.** If one worker is best, say why.
4. Implement in small units, each ending in a check (**Sequence verifiable
   units**). Delegate with file paths, the named shape and success criteria,
   or implement directly when coordination costs more than it saves.
5. Verify on the real surface: `create-verification` for supported Defuse work.
   Inconclusive or wrong-surface is not a pass.
6. Keep commits small and ordered, each landable and green.
7. If the design is contested, run `interrogate` before shipping.
8. Ship with `ship` when authorized; otherwise stop at the local checkpoint.

**Reply:** what you built, what you chose and why, the throughput checkpoint and
open decisions. Use a table for design alternatives.

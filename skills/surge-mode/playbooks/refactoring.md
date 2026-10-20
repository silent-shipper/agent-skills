# Refactoring

**You own the contract.** The structure changes; the behavior and UI/UX do not.
If the cleanup reveals a missing feature or a real bug, split it out and ship the
structural change first against the pinned contract.

1. Pin the behavior first. Run `how` to learn the contract, then capture current
   behavior with a characterization test, snapshot or equivalence harness before
   anything moves. Typecheck and lint are not a pin.
2. Compare against leaving the code alone. Name the structure the code is
   missing (**Model the domain**); the reshape must delete branches or invalid
   states, not add indirection. If you proposed the refactor and it does not pay
   for itself, recommend leaving it and stop. If the user asked for this
   specific change, do it and state any concern.
3. Name the target shape: module layout, types and call graph as if built
   today. If it crosses a module boundary, run `architect`.
4. Subtract before you add: within the code being restructured, delete dead
   code, one-caller wrappers, redundant validators and orphan references before
   introducing the new shape.
5. Move in small steps that keep the pin green. For an API reshape, migrate
   every caller and delete the old API in the same change; no compatibility
   shims or parallel paths. Check every rename against strings, docs and
   back-references.
6. Prove behavior is unchanged on the real artifact (**Prove it works**), with
   `create-verification` for supported Defuse work. For
   larger reshapes, diff old against new outputs or replay a recorded baseline.
7. Order commits: subtraction, then reshape, then follow-on cleanup.
8. Ship with `ship` when authorized; otherwise stop at the local checkpoint.

**Reply:** what structure changed, the pin it held against, the equivalence
proof, what got simpler for the next reader, and anything reverted.

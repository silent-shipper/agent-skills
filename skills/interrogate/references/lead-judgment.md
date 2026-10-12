# Lead judgment

The lead filters rather than votes.

## Validate before accepting

- Trace the actual caller and input path for hypothetical failures.
- Treat multi-reviewer agreement as a prioritization signal, not proof.
- Scrutinize lone-reviewer security and correctness claims even without consensus.
- Reject findings about untouched code unless the change makes an existing problem reachable or materially worse.
- Reject "I would implement it differently" unless it identifies a concrete defect, maintenance cost, or violated project convention.
- Reject premature abstractions that lack a second real use or clear invariant benefit.
- Apply known timeline, migration, stack, and architectural context that reviewers lacked.

## Calibrate the verdict

`Act on` should contain only issues that would block a responsible shipment. More than a handful usually means the lead has not deduplicated or prioritized enough. `Consider` captures real tradeoffs. `Noted` preserves context without manufacturing work. `Dismissed` is a trust mechanism: show what was rejected and why.

An empty `Act on` section is a valid and useful outcome.

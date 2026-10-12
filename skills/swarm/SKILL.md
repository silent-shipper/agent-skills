---
name: swarm
description: Fan out independent work across slices, coverage lanes, experiments, or declared race arms, then return one evidence-backed report. Use when the user says "swarm this" or when parallelism materially improves coverage or latency. Do not use when candidates must solve the same problem and be synthesized; use arena instead.
---

# Swarm

Partition independent work, run it concurrently, drain every lane, and consolidate the evidence. This skill explicitly calls for parallel subagents when collaboration tools are available.

## Frame

Track Frame, Fan out, Aggregate, and Report in the task plan.

1. State the done predicate and final artifact or report.
2. Choose the shape:
   - **Slices:** different packages, files, cases, or research areas.
   - **Race:** identical goal with declared arms or approaches.
   - **Mixed:** partitioned slices with a race inside selected slices.
3. For a race, declare the selection rule before spawning: `first pass`, `rank all`, or `best of` against explicit criteria.
4. Set worker count from the coverage shape and available concurrency. Do not create redundant workers without a distinct slice or race arm.
5. Make every brief self-contained: goal, exact scope, exclusions, verification, and required evidence.

## Fan out

Spawn all independent workers concurrently. Use inherited models unless the user or governing instructions explicitly request model overrides.

Each worker reports exactly one of:

- `PASS` with evidence.
- `ISSUES` with concise evidenced findings.
- `BLOCKED` with the blocking condition and completed checks.

When workers write, assign non-overlapping files or separate worktrees/directories. Never allow concurrent writes to shared mutable state. Workers must not broaden scope or perform external mutations not authorized by the original task.

If a worker drops out, continue where useful and explicitly report the uncovered slice. Reassign a required slice when capacity and time allow.

## Aggregate

Wait for all workers. For coverage, ensure every required slice has a terminal result. For races, apply the selection rule declared before launch. Verify important artifacts directly when possible; do not treat worker self-reports as proof when the output can be inspected or tested.

Deduplicate overlapping findings and preserve the strongest evidence. Do not paste raw worker dumps.

## Report

Return one compact consolidated report containing:

- A result table by slice or race arm.
- One-line evidenced issues.
- The race rule and winner, when applicable.
- Explicit gaps, blockers, and dropouts.
- Overall conclusion and relevant next action.

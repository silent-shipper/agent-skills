---
name: architect
description: Design types, interfaces, ownership, and module boundaries before implementation. Use when a feature or refactor crosses boundaries, changes ownership, creates a durable API, or when the user says "architect this" or "design this". Do not use for small localized edits.
---

# Architect

Settle the shape before filling in implementation. Optimize for a small caller-facing surface that hides complexity and keeps ownership clear.

## Workflow

Track these phases in the task plan: Ground, Sketch, Select, Implement, Reassess.

### Ground

Trace the real system the design touches: callers, callees, data flow, state ownership, validation boundaries, invariants, and existing tests. If ownership or layering will move, inspect history or decision records when available so the current shape's rationale becomes a constraint rather than a guess. Skip only for genuinely isolated greenfield work.

### Sketch

Use [design-red-flags.md](references/design-red-flags.md) to challenge the boundary. For a substantial design, use [design-package.md](references/design-package.md).

Write the caller's usage first, then derive types, signatures, ownership, module boundaries, data flow and verification. Reuse the existing shape when it satisfies the requirements. Compare structurally distinct alternatives when the boundary remains uncertain. Use `$arena` when explicitly requested or when an expensive, hard-to-reverse decision benefits from independent candidates; a settled boundary does not require delegation.

When `architect` and `arena` are requested together, run one shared design comparison for that decision. Reuse a previous comparison only after locating its candidate outputs and synthesis in the session or an artifact and checking the grounding against the current baseline, requirements and affected boundaries. Cite the reused evidence and revision. If that evidence is unavailable or stale, refresh the needed comparison rather than claiming reuse. Read the detailed design-package reference only when the scope needs it.

Prefer the design that hides more policy and complexity behind the smaller coherent interface. Reject or revise shapes with information leakage, temporal decomposition, shallow wrappers, or unclear shared-state ownership.

### Select

Synthesize one design package and record why it won, what was incorporated from alternatives, and what was rejected. Continue directly into implementation unless the user asked for a checkpoint. At a requested checkpoint, show the design and wait before editing implementation files.

### Implement

Implement against the selected shape and verify proportionally to risk. Treat deviations as evidence: if implementation needs unexpected parameters, type escape hatches, shared state, or caller knowledge of internals, determine whether the requirement was missed or the design is wrong. Do not silently bolt exceptions onto the design.

### Reassess

Redesign when the same workaround pattern appears at least twice across independent parts of the implementation, multiple special cases all fight the same boundary, or callers repeatedly need internal knowledge. Re-ground using what implementation taught, simplify the shape, and run the design comparison again. A single hard edge case is not enough to condemn the architecture.

## Output

For small work, provide a compact usage sketch plus types and signatures. For larger work, provide the complete design package described in the reference. Keep rationale alongside the design only when it will help reviewers or future maintainers; do not create documentation or commits unless the task calls for them.

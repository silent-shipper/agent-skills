---
name: arena
description: Run multiple independent candidates on the same non-trivial artifact, select the strongest base against a rubric, incorporate the best compatible ideas, and verify the synthesis. Use when the user says "arena this" or when one attempt would prematurely lock in an expensive decision.
---

# Arena

Use independent attempts to explore the same problem, then synthesize one coherent result. This skill explicitly calls for parallel subagents when collaboration tools are available.

## Frame

Track Frame, Fan out, Judge, Synthesize, and Verify in the task plan.

Before delegating:

1. State the exact artifact every candidate must produce.
2. Create three to six concrete, gradeable criteria from the user's goal. Avoid generic criteria such as "correct" without an observable meaning.
3. Choose the candidate count from the decision cost and available concurrency. Default to three; use two for a narrow decision and four or more only when distinct directions are plausible and the decision is expensive.
4. Give every candidate the same task, grounding, constraints, and output contract. Do not show candidates the grading rubric when independent generation would be biased by it.

## Fan out

Spawn candidates concurrently. Each produces the artifact or proposal plus a short rationale naming alternatives considered and rejected.

For proposals and reviews, keep agents read-only and collect results in their responses. When candidates must write code, isolate their writable targets with separate worktrees or explicit non-overlapping directories; never let candidates edit the same files concurrently. Preserve authorization boundaries and do not create remote branches or PRs unless requested.

Use inherited agent models by default. Only select model overrides when the user or governing instructions explicitly request them. Independence of attempts is still valuable without model diversity.

Proceed with successful candidates if one drops out, and record the gap. If fewer than two usable candidates remain, replenish or report that the arena comparison could not be completed.

## Judge

The lead reads every candidate and scores it against the rubric. Add an independent read-only judge when the decision is expensive or a material disagreement remains; do not add one solely because a concurrency slot is free. Give the judge the rubric and labeled candidate outputs. Resolve disagreement by tracing both rationales and the underlying evidence.

## Synthesize

Select the base that best satisfies the rubric and is easiest to extend without breaking invariants. Prefer the cleaner boundary and smaller coherent surface when tied.

Incorporate only compatible high-value ideas from losing candidates. Re-express them in the base's mental model rather than pasting mechanically. If candidates converge, record the consensus and avoid gratuitous grafting. If they diverge wildly, the prompt was likely underspecified: reframe and rerun instead of averaging incompatible designs.

Record a compact synthesis note containing the base, scoring rationale, incorporated ideas and their sources, rejections, dropouts, and verification result.

## Verify

Verify the synthesized artifact using the same checks ordinary work requires. The arena process is not evidence that the result works. If verification fails, decide whether framing was wrong or a useful candidate insight was missed, then return to that phase.

Return one synthesized artifact. Reuse its grounding, decision and proof when another skill in the same task needs that result. If no new failure, requirement or boundary evidence appears, the completed comparison is sufficient; do not restart it to pursue an unmeasurable claim of perfection.

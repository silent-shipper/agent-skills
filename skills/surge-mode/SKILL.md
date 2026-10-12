---
name: surge-mode
description: "Apply Surge's working style: understand the real outcome, prove the simplest complete solution, preserve scope and behavior, and communicate concise decisions. Use when asked for surge-mode or to work in Surge's style."
---

# Surge mode

Spend the effort to find and prove the simplest complete solution. Keep the
implementation and explanation lean. The user should not have to supervise
basic completeness or repeatedly strip unnecessary complexity from the result.

## Understand and own the task

- Establish the real outcome and existing behavior before choosing an approach.
  Inspect current code, relevant PRs, and stack dependencies, including work
  already merged or underway.
- Respect the requested checkpoint: research, plan, draft, local work, or shipping.
  Within authorized implementation, resolve supported issues and reverify instead
  of returning work you can finish yourself.
- Follow requested skills and verification steps. Disclose missing prerequisites
  and omitted steps. Do not silently substitute an easier task.

## Make the change worth its cost

- Meet the full agreed scope with reuse, deletion, and fewer moving parts.
  Justify added files, wrappers, fallbacks, flags, and abstractions by a present
  requirement. Investigate unexpected diff growth. When correctness requires a
  larger change, explain why.
- For refactors, compare against keeping the current implementation. Prove a
  meaningful maintenance benefit while preserving behavior and UI/UX. Recommend
  leaving it alone when the benefit does not justify the change.
- Use `architect` for uncertain ownership or boundaries; use `arena` when
  explicitly requested or independent alternatives justify their cost. A combined
  request shares one design comparison. Reuse completed grounding and proof, and
  rerun only when new requirements or evidence change the decision. Prove the
  smallest useful integration before proposing a broader redesign.
- Prefer self-explanatory code. Keep narration comments and incidental docs or
  reports out of implementation diffs; maintain required project documentation.

## Verify and exercise judgment

- Reproduce failures and trace their cause. Compare affected user flows with the
  baseline. Check account and environment prerequisites. Use `create-verification`
  for supported Defuse work.
  Run browser tests headlessly unless the user asks to watch.
- Use requested adversarial and quality reviews to challenge correctness and
  complexity. Fix supported findings and reverify. Report the proof obtained
  and distinguish product failures from environment failures.
- Separate introduced regressions, existing issues, and optional improvements.
  Establish realistic impact before calling an issue a blocker. Account for
  removed features and demo-only scope.
- Treat "principal engineer approval" as a demand for rigorous judgment.
  Give a clear recommendation without inventing approval or promising zero bugs.
- For UI work, inspect real screens, loading, navigation, and user actions.
  Respect the design system and requested visual scope.
- When shipping and CI follow-through are requested, finish both and verify the
  relevant PR head and checks before reporting completion.

## Make the answer easy to act on

- Lead with the decision, outcome, or blocker. Explain what changes, why it is
  worth doing, and what was verified. Use plain language and cut process narration.
- Use `breakdown` for change summaries and code/test file counts. Label estimates.
  Explain architecture with a short before/after when useful. Keep detailed
  research behind the concise answer when requested.
- Keep project rules and workflow mechanics in their existing owners. Load only
  the relevant skills.

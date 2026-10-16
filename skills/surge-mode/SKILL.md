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

## Route the work

For a long task, record its class, requested endpoint, observable done predicate
and proof in the existing task plan. Keep completed decisions and evidence there;
refresh them only when inputs change. Small localized tasks need no extra ledger.

Each trigger below is mandatory when it fires. Read the named skill in full
before acting on it, and in the reply name each skill that changed a decision
and the decision it changed. Load only skills whose trigger fired.

| When | Use |
| --- | --- |
| Asked to confirm the prompt, or the request is ambiguous or high-stakes | `sharpen`, then wait for confirmation |
| Resuming work, "catch me up", or learning from past sessions | `recall` |
| How code works, where behavior lives | `how` (read-only) |
| Why code is shaped this way, before changing defensive or odd code | `why` |
| Code crossing a module boundary, or new ownership | `architect` before implementing |
| Expensive decision with real alternatives, or "arena this" | `arena` |
| Independent slices, coverage lanes or experiments | `swarm` |
| A fork answerable by running something (behavior, timing, output) | prototype it and let the result decide; ask only product or preference calls |
| Supported Defuse feature or bug | `create-verification` for proof |
| Measured performance or reliability claim | `benchmark-checklist` before reporting |
| Small diff whose wider impact is untrusted | `blast-radius` |
| Contested design, or before shipping a risky change | `interrogate` |
| Maintainability audit or "thermo-nuclear" | `thermo-nuclear-code-quality-review` |
| Same correction a second time, or "make this impossible" | `correct`: enforce it in structure, not prose |
| Long, unattended or multi-phase run | `show-me-your-work` decision log |
| Commit, push, PR, CI follow-through | `ship` |
| Any user-facing prose: reply, PR body, review comment | `unslop`, and `breakdown` for change summaries |
| Asked for a guided review | `review-guide` |
| Session learnings or skill improvements | `reflect` |

Reuse a suitable isolated checkout. A new independent task may start from the
current default branch; PR fixes and dependent work use their actual target/base.
Use the app's setup guidance. Managed verification owns server startup; start a
caller-owned preview only when requested. Worktree creation is ordinary Git/T3
setup and does not need a separate skill.

## Make the change worth its cost

- Meet the full agreed scope with reuse, deletion, and fewer moving parts.
  Justify added files, wrappers, fallbacks, flags, and abstractions by a present
  requirement. Investigate unexpected diff growth. When correctness requires a
  larger change, explain why.
- For refactors, compare against keeping the current implementation. Prove a
  meaningful maintenance benefit while preserving behavior and UI/UX. Recommend
  leaving it alone when the benefit does not justify the change.
- A combined `architect`/`arena` request shares one design comparison. Reuse completed grounding and proof, and
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
- Use `breakdown`'s fixed shape for change summaries and file counts. Label estimates.
  Explain architecture with a short before/after when useful. Keep detailed
  research behind the concise answer when requested.
- Keep project rules and workflow mechanics in their existing owners. Load only
  the relevant skills.

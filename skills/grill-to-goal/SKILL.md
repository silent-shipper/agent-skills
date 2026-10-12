---
name: grill-to-goal
description: A relentless interview that sharpens a plan or design, captures docs (glossary + ADRs) as it goes, then distills a concise goal and dispatches /goal to execute it autonomously. Use when the user wants to stress-test a plan before an autonomous build, or uses any 'grill' trigger phrase.
disable-model-invocation: true
---

# Grill to Goal

A relentless interview that sharpens a plan or design, writes the docs as it goes,
then hands a concise goal to `/goal` for autonomous execution. Three phases, in order:
**grill → capture → goal.**

## Phase 1 — Grill

Interview the user relentlessly about every aspect of the plan until you reach a shared
understanding. Walk down each branch of the design tree, resolving dependencies between
decisions one by one. For each question, provide your recommended answer.

Ask the questions one at a time, waiting for feedback on each before continuing. Asking
multiple questions at once is bewildering.

If a question can be answered by exploring the codebase, explore the codebase instead of
asking.

## Phase 2 — Capture as you go

While grilling, actively build and sharpen the project's domain model. Write the glossary
and decisions down the *moment they crystallise* — don't batch them.

### File structure

Most repos have a single context:

```
/
├── CONTEXT.md
├── docs/
│   └── adr/
│       ├── 0001-event-sourced-orders.md
│       └── 0002-postgres-for-write-model.md
└── src/
```

If a `CONTEXT-MAP.md` exists at the root, the repo has multiple contexts and the map points
to where each one lives (per-context `CONTEXT.md` + `docs/adr/`). Create files lazily — only
when you have something to write. Create `CONTEXT.md` when the first term is resolved;
create `docs/adr/` when the first ADR is needed.

### During the interview

- **Challenge against the glossary.** When a term conflicts with existing language in
  `CONTEXT.md`, call it out immediately. "Your glossary defines 'cancellation' as X, but you
  seem to mean Y — which is it?"
- **Sharpen fuzzy language.** When a term is vague or overloaded, propose a precise canonical
  term. "You're saying 'account' — do you mean the Customer or the User? Those are different."
- **Discuss concrete scenarios.** Stress-test domain relationships with specific scenarios
  that probe edge cases and force precision about boundaries between concepts.
- **Cross-reference with code.** When the user states how something works, check whether the
  code agrees. Surface contradictions: "Your code cancels entire Orders, but you just said
  partial cancellation is possible — which is right?"
- **Update `CONTEXT.md` inline.** When a term is resolved, write it right there — don't batch.
  Use the format in [CONTEXT-FORMAT.md](./CONTEXT-FORMAT.md). `CONTEXT.md` is a glossary and
  nothing else — totally devoid of implementation details. It is not a spec or a scratch pad.
- **Offer ADRs sparingly.** Only offer an ADR when all three are true: (1) hard to reverse,
  (2) surprising without context, (3) the result of a real trade-off with genuine
  alternatives. If any is missing, skip it. Use the format in [ADR-FORMAT.md](./ADR-FORMAT.md).

## Phase 3 — Goal

When you and the user reach shared understanding, distill the interview into a **simple,
straightforward, concise goal plan**:

- **Objective** — one or two sentences: what "done" looks like.
- **Scope / non-goals** — what is in, and what is explicitly out.
- **Done-criteria** — checkable conditions that mean the goal is met.
- **References** — point to `CONTEXT.md` and any ADRs written in Phase 2.

Keep it tight. It is a goal, not a spec — the Phase 2 docs hold the detail; the plan points
to them.

Show the plan and confirm in one line: *"Execute this? (go / edit)"*. On `go`, dispatch
`/goal` with the plan so the agent works on it autonomously to completion.

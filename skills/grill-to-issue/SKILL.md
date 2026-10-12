---
name: grill-to-issue
description: Turn vague roadmap items, epics, product ideas, dependency work, or feature requests into concise private Notion issue-draft one-pagers through a focused grill. Use when the user says "grill to issue", wants to create or update a draft issue brief from a roadmap item, or wants product, technical, design, QA, ops, or dependency expertise added to an existing Notion draft before it becomes a GitHub issue.
---

# Grill To Issue

Turn ambiguous work into a buildable issue draft. The draft lives as a private Notion one-pager until approved: clear enough for a human or agent to build from, small enough to keep the team out of fog-of-war execution.

Follow four phases in order: **ground -> grill -> draft -> apply**.

## Phase 0 - Ground

Before asking the first question, inspect available context when it can answer the question better than the user can:

- Search the repo for current surfaces, routes, state, feature flags, tests, and existing domain language.
- Search Notion or linked docs when the user references a plan, strategy, roadmap, or prior decision.
- Search GitHub issues and PRs when available to avoid duplicate work or stale assumptions, but do not create or update GitHub from this skill.
- Fetch an existing Notion draft first in update mode.

Then show a short context packet:

```markdown
Grounding:
- Source docs:
- Existing product/code surfaces:
- Current behavior:
- Constraints:
- Unknowns:
```

Keep the packet factual. If a claim depends on repo behavior, ground it in inspected files or say it is an inference. Do not invent new flows when a current surface already exists.

## Phase 1 - Grill

Start by identifying the roadmap item, the intended pass, and the target draft:

- **Create mode**: no draft exists yet; produce a new private Notion issue-draft one-pager.
- **Update mode**: a Notion draft already exists; add or sharpen one area without bloating the page.
- **Pass type**: product, technical, design / UX, QA, ops / observability, dependency, or general.

If the source includes roadmap metadata, carry it forward tersely: item name, type, effort, confidence, owner, dependency, and source link if available.

Ask one question at a time. For every question, include the recommended answer and why it is likely correct. Do not ask a question that the repo, Notion, or existing issue context already answered.

Challenge vague language immediately. Replace words like "support", "improve", "integrate", "proper", "done", "fast", or "polished" with concrete behavior and scope.

Stop grilling when the draft can answer:

- Why are we doing this?
- Who or what system benefits?
- What is in scope?
- How should the epic be broken down?
- What outside-team dependencies can block it?
- Should this draft include a `Technical Design` section, or stay product-level?

Do not over-grill small chores. If the issue is already clear enough after grounding, draft it.

## Corrections

When the user corrects a fact or direction:

- Lock the correction in one sentence.
- Remove stale assumptions from the working draft.
- Re-ground if the correction contradicts repo or Notion context.
- Continue from the corrected model instead of asking from the old frame.

## Phase 2 - Draft

Draft the smallest useful Notion issue brief. Keep it concise, direct, and easy to scan. Prefer concrete bullets over long paragraphs.

Default to this product-level structure:

```markdown
# <clear issue title>

## Problem
<1-3 sentences on the user, business, or system problem.>

## Outcome
<What should be true when this ships.>

## Scope
- <Included behavior or deliverable>

## Dependencies
- <Outside-team dependency, owner, readiness signal, or unresolved assumption>

## Open Questions
- <Only questions that truly block or materially change scope>
```

Do not include sections just because a template has them. Negotiate the section set from the work:

- Add `Technical Design` only when the user requests a technical pass, approves adding it, or the task is explicitly technical.
- Add QA notes only when they materially clarify the work.
- Add launch / GTM notes only when the draft is partly a market-facing launch brief.
- Remove empty or irrelevant sections.

Optional section:

```markdown
## Technical Design
- <Implementation shape, API/data contract, migration concern, or rollout note>
```

Do not hallucinate a build plan from weak context.

## Dependencies

Dependencies mean outside-team or external-system work required before this can ship. They are not local implementation surfaces.

Good dependency examples:

- Bridge team exposes required route support.
- Data team provides an event or dashboard.
- Partner API is available in production.
- Design delivers final copy or interaction rules.

Bad dependency examples:

- Existing React component names.
- Existing query hooks.
- Existing routes.
- Tests that should be added by the implementation owner.

## Pass Guidance

- **Product pass**: sharpen problem, user value, scope, outcome, roadmap fit, and user-facing behavior.
- **Technical pass**: ask to add `Technical Design`, then add implementation shape, API/data contracts, architecture constraints, rollout, feature flags, and migration concerns.
- **Design / UX pass**: add flows, states, copy constraints, accessibility, empty/error/loading states, and edge-case interaction rules.
- **QA pass**: add critical paths, fixtures, e2e coverage, regression coverage, and manual QA notes when they materially clarify the work.
- **Ops / observability pass**: add metrics, logs, dashboards, alerts, thresholds, and rollback signals.
- **Dependency pass**: add outside-team owner, required contract, readiness signal, fallback, and unblock date if known.

For large epics, break work into coherent slices without turning the draft into a full project plan. If a slice is large enough to require separate implementation, note it as a child issue candidate.

## Phase 3 - Apply

Before touching Notion, show the exact page create/update:

- Title
- Body
- Parent destination: `Private Notion page` unless the user explicitly gives another draft destination
- One-line summary of what changed in update mode

Ask: `Create/update this private Notion draft? (go / edit)`.

Only create or update Notion after approval. If the user says `edit`, revise the draft first. If Notion access is unavailable, provide the approved page body and say what could not be applied.

When creating the Notion page:

- Fetch `notion://docs/enhanced-markdown-spec` first when the tool supports it.
- If the spec is unavailable, use only conservative Markdown: headings, short paragraphs, bullets, numbered lists, inline code, and links.
- Create a standalone private page by omitting the parent unless the user explicitly provided a draft parent.
- Prefix the title with `[Draft]` unless the user asks for another naming convention.
- Return the Notion URL after creation.
- Fetch the created page once to verify title and content.
- Do not create a GitHub issue; that is a later publishing step after the draft is approved.

## Update Mode Rules

When adding expertise to an existing Notion draft:

- Fetch the current Notion page first.
- Preserve existing decisions unless they are contradicted by newer context.
- Update the relevant section instead of appending duplicate content.
- Replace stale open questions with decisions when resolved.
- Compress the page if the update makes it too long.
- Keep unresolved uncertainty visible, but do not let it dominate the brief.

The same draft may receive multiple passes. Each pass should make the future issue more buildable, not larger by default.

## Quality Bar

A good `grill-to-issue` output is boringly clear:

- The grounding packet matches the existing product/code reality.
- A developer can start without reopening basic questions.
- A reviewer can tell whether the PR matches the draft.
- QA knows the critical paths when QA detail is included.
- Design knows which states and interactions matter when design detail is included.
- Ops knows which signal catches breakage after merge when ops detail is included.

Avoid vague outcomes, hidden dependencies, giant specs, unsourced assumptions, and polished language that does not reduce execution ambiguity.

---
name: reflect
description: Spawn three parallel reviewers over the active conversation, identify durable learnings, and propose concrete skill edits. Use when the user asks to reflect, /reflect, or $reflect on the session.
---

# Reflect

Mine the current conversation for durable learnings and route each to its owner.
This skill is explicitly invoked; `agents/openai.yaml` disables implicit use.
Installing, quoting, or discussing this skill does not invoke its workflow.

Skip review when the conversation is trivial, off-topic, or demonstrates only
guidance already present and correctly followed. A one-off is not a pattern.

## 1. Establish the evidence

Use the exact active transcript path or workspace transcript directory supplied
by the session or user. Never search global chat stores or other workspaces.
For a supplied directory, inspect only its immediate transcript files and the
documented nested layouts: `<id>/<id>.jsonl` and
`<parent>/subagents/<child>.jsonl`. Verify the parent conversation using its
opening user request and a later distinctive turn; do not select a child log
as the full session. Parse the actual format instead of assuming one JSON key.

If no scoped path is supplied or no candidate matches, prepare a concise digest
from the visible conversation. Include the request, important decisions,
corrections, tools and skills actually used, outcomes, and unresolved points.
Assign digest item IDs and distinguish quotes from paraphrases. State that the
digest may omit earlier context. Do not invent transcript lines or evidence.

Give every reviewer the same source and the relevant skill catalog and paths.
Read only directly referenced external context, using read-only connector calls.
Keep credentials, secrets, and unrelated private content out of reviewer prompts.

## 2. Launch three independent reviewers

Use `collaboration.spawn_agent` for each reviewer before waiting for results.
Use `fork_turns: "none"` and pass the source and context explicitly. These
reviewers need tools for evidence gathering but must not mutate files or services.
Do not assume a Cursor `Task` tool, `generalPurpose` role, or `readonly` flag.

Use a user-configured, available model for each lens when provided. Otherwise:

| Lens | Model | Reasoning | Template |
|---|---|---|---|
| Judgment | `gpt-6-astra` | `max` | [judgment-reviewer.md](references/judgment-reviewer.md) |
| Tooling | `gpt-5.6-sol` | `max` | [tooling-reviewer.md](references/tooling-reviewer.md) |
| Divergent | `gpt-6-astra` | `max` | [divergent-reviewer.md](references/divergent-reviewer.md) |

Pass the template verbatim, replacing `{{SOURCE}}` and `{{SKILL_CONTEXT}}`.
If a configured model is unavailable, inherit the parent model by omitting the
model and reasoning overrides, and disclose the substitution. Never invent a
model ID. Reviewers return their complete findings in their final response.

If parallel agents are unavailable, report the limitation. A parent-only review
must not be described as three independent reviews.

## 3. Synthesize

After all three reviewers finish, spawn a separate synthesizer using the
judgment model and [synthesizer.md](references/synthesizer.md). Substitute the
source, skill context, and each reviewer's full output into the marked fields.
The synthesizer verifies evidence and target skills without making changes.

Inspect its Accepted, Rejected, and Backlog lists. Move proposals better enforced
by a lint rule, script, metadata setting, or runtime check into Backlog. Reject
prose that duplicates a mechanism or guidance already working correctly.

## 4. Present proposals and obtain approval

Show the complete Accepted / Rejected / Backlog result, including the concrete
replacement or insertion text for every Accepted edit. Stable item IDs let the
user approve a subset or redirect its routing.

Wait for explicit approval of the concrete Accepted edits before changing any
skill. Invoking reflect authorizes analysis, not unseen edits. When asking,
link to this SKILL.md and quote this approval requirement so the pause is clear.
Apply only the approved subset. A materially changed proposal needs new approval.

For Backlog items, use the team's explicitly configured or session-designated
devex tracker automatically when available. Check duplicates before creating
issues and include evidence, suggested mechanism, and acceptance criteria.
If no destination is established or access is unavailable, return unfiled items
in the report; do not guess a workspace, project, or recipient. Do not post to
chat or send email. Report only confirmed issue creation as filed.

## 5. Apply and validate

Follow each approved Routing field:

- A trivial existing-skill edit: the parent applies it directly.
- A substantive edit, new section, or more than about ten lines: use
  `skill-creator` for authoring and proportionate validation.
- `tune description: <skill path>`: use `skill-creator`; check realistic matching
  and nonmatching requests to avoid broadening the trigger accidentally.
- `new skill via skill-creator: <kebab-name>`: use `skill-creator`; create only
  when recurring evidence has no suitable existing owner.

Read each target again before editing and preserve unrelated changes. Respect
personal versus project scope; do not edit generated plugin-cache files as if
they were durable sources. If the approved owner is not writable or durable,
report that constraint and obtain approval for an alternate destination.

Run the installed `skill-creator` validator on every touched skill, and verify
referenced files and invocation metadata. Report any validation limitation.

## 6. Report

Use a short list with no preamble; omit empty categories:

- Edits applied: skill path and one-line change.
- New skills created: skill path and purpose.
- Backlog filed: issue title, tags, and confirmed link.
- Backlog unfiled: item and missing destination or access.
- Pending approval: item IDs not applied.
- Dropped: rejected finding and reason.

Workflow adapted from the user-supplied
[Cursor reflect skill](https://github.com/cursor/plugins/blob/main/pstack/skills/reflect/SKILL.md)
and its reviewer references for Codex tools and invocation metadata.

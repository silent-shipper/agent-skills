---
name: how
description: Explain how a subsystem works from source and runtime evidence, including data flow, ownership and where behavior lives. Use for code walkthroughs and how/where/which-layer questions; it does not implement a change.
---

# How

Build a working mental model of the requested flow. Answer the question at the
user's level; do not narrate every file you opened.

Trace the actual entry point through callers, state/data ownership, boundaries
and observable output. Read relevant tests and domain/decision documentation.
Use runtime evidence when source cannot settle a behavior. Distinguish observed
behavior, intended contract and inference. For historical motivation, inspect
history or linked decisions rather than guessing why the author chose it.

Handle a narrow question directly. For independent subsystem slices, use the
available read-only delegation tools only when the extra coverage is worthwhile.
Give every worker a concrete question and source scope; verify important claims
yourself. Do not require a particular provider, model or agent API.

Start with a concrete flow or before/after mental model. Add only the concepts
needed to follow it, the owning files with source links, and meaningful gotchas.
Call out unresolved evidence. A recommendation may identify a better owner, but
this read-only explanation does not authorize implementation, new documents,
account actions or service startup.

Adapted from [Lauren Tan's pstack how](https://github.com/cursor/plugins/blob/1dcc2bacde73ddd284803b7af28164d0436198fc/pstack/skills/how/SKILL.md). See [LICENSE](LICENSE).

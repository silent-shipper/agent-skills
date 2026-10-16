---
name: breakdown
description: Boil a PR, implementation, or plan down to an ultra-concise summary of what changed or will change, including file counts.
---

Use this fixed shape, one short bullet group each and nothing else:

- **Changes:** what the change does for the user or system, one bullet per
  meaningful change.
- **Why:** why it is worth its cost, one line.
- **Verified:** each change's proof: test, browser run with link, or "not
  verified". When several changes or worktrees are in play, use a table:
  change | worktree/branch | browser-verified (yes/no + link) | blocker.
- **Gaps:** what remains unproven or blocked. Omit when none.

Lead with what the change actually does for the user or system, then why the approach is worth its cost. For a small change, use roughly 4–6 short bullets; use up to 20 only when the scope warrants it. Cover meaningful changes, relevant proof and material remaining gaps. Merge related work, omit process narration and minor details, use plain language, and never invent missing information. Include risk only when there is concrete impact or uncertainty to explain.

When the user asks for simple, ADHD-friendly, or mental-model-first communication, begin with one concrete before/after model or three-step flow. Follow it with compact technical mapping, impact, proof, gaps, and file counts. Keep the normal mode concise.

End with one bullet formatted `Files: N total — T tests, C code`. For a PR or completed implementation, inspect and report actual changed-file counts; for a plan, give clearly approximate estimates (for example, `Files (estimated): ~8 total — ~3 tests, ~5 code`). Count every non-test file as code so the categories add up to the total.

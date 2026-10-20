---
name: status
description: "Ultra-concise catch-up on what changed in this chat since the user's last message and what waits on them, under 80 words. Use for /status, 'where are we', 'catch me up' within this conversation, the end of a plan, implementation or PR review, and the final reply of a long or unattended run."
---

# Status

Adapted from pstack `ketchup` and `bro` (MIT, Lauren Tan).

The user should take the reply in at a glance. When in doubt, cut. Details stay
available on request; they do not go in the reply.

## Gather

Stay read-only. Collect what changed since the user's last message: your work,
subagent reports and anyone else's messages. Check the live state of each PR,
CI run or agent this chat touched, and check every number against its source.
Past sessions and other threads belong to `recall`.

A decision is a call only the user can make: a product choice, an approval, an
irreversible action, or access you lack. Work you can still do is not one.

## Shape

```markdown
**<Outcome in one sentence.>**

- <What changed for the user, at most 12 words.>

**Proof:** <how it was checked, one line.>
**Gaps:** <only if material, one line.>
**Needs you:** <the call and your pick, at most 20 words.> | Nothing.

Files: N total — T tests, C code
```

- At most 80 words above **Needs you**. At most 3 change bullets; merge
  related changes and drop anything the user would not miss.
- One **Needs you** line per decision, never dropped to save words; combine
  decisions that share a call. Leave out low risk; state a real risk in a few
  words.
- Plain words, like one person telling another. No headers beyond the shape,
  no tables, no sub-bullets, no tool, skill or agent names, and no hashes,
  paths or commands unless the user needs one to act.
- Never mark something done that still waits on the user. Never invent a
  number or a link.
- One inline screenshot only when the change is visible. No diagrams unless
  asked.
- `Files:` only for completed changes, from the actual diff; for a plan write
  `Files (estimated): ~N total — ~T tests, ~C code`. Count every non-test file
  as code.
- If the user asks for more, expand only the part they asked about.

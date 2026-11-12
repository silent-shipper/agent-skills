---
name: status
description: "Give a concise catch-up or a complete current snapshot of an existing board, roadmap or agenda. Use for /status, 'where are we', 'catch me up' within this conversation, requests to refresh or condense an existing board, roadmap or agenda, the end of a plan, implementation or PR review, and the final reply of a long or unattended run. Keep narrative under 80 words without dropping requested items."
---

# Status

Adapted from pstack `ketchup` and `bro` (MIT, Lauren Tan).

The user should take the reply in at a glance. When in doubt, cut. Details stay
available on request; they do not go in the reply.

## Gather

Stay read-only. Choose a delta update or a complete snapshot from the request.
For a refresh or condensed version of an existing list, collect the complete
current state within its requested scope. For a delta update, collect changes
since the user's last message: your work, subagent reports and anyone else's
messages. Check the relevant live PR, CI and agent state, and check every number
against its source. Past sessions and other threads belong to `recall`.

A decision is a call only the user can make: a product choice, an approval, an
irreversible action, or access you lack. Work you can still do is not one.

## Shape

```markdown
**<Outcome in one sentence.>**

- <What changed for the user, at most 12 words.>

**Proof:** <where each changed behavior ran and the result: real browser against real services, browser with named mocks, tests only, or not run.>
**Gaps:** <only if material, one line.>
**Needs you:** <the call and your pick, at most 20 words.> | Nothing.

Files: N total — T tests, C code
```

- At most 80 words above **Needs you**. At most 3 change bullets; merge
  related changes and drop anything the user would not miss.
- When the request refreshes or condenses an existing board, roadmap or agenda,
  replace the change bullets with the complete current list. Shorten each
  item's explanation, not the list of in-scope items. Give each item its
  current state and next action or decision, where applicable. These item
  lines are outside the narrative word cap and three-change-bullet limit.
- For several PRs, use one linked line per independent PR or stack and preserve
  the requested readiness groups. A stack is one decision unit; link its member
  PRs.
- One **Needs you** line per decision, never dropped to save words; combine
  decisions that share a call. Leave out low risk; state a real risk in a few
  words.
- Plain words, like one person telling another. No headers beyond the shape
  and the PR groups, no tables, no sub-bullets, no tool, skill or agent names,
  and no hashes, paths or commands unless the user needs one to act. Write
  every PR as a link.
- Never mark something done that still waits on the user. Never invent a
  number or a link. Say verified or done in the outcome only when every
  changed behavior passed where a user would exercise it, which for UI means a
  real browser; otherwise name what did pass.
- When completed work changed visible UI, show one inline screenshot of the
  result, captured from the running app after the change. If capture failed,
  say so in one line under **Gaps**. No other images, and no diagrams unless
  asked.
- `Files:` only for completed changes, from the actual diff; for a plan write
  `Files (estimated): ~N total — ~T tests, ~C code`. Count every non-test file
  as code.
- If the user asks for more, expand only the part they asked about.

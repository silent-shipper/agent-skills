---
name: correct
description: "Find the mistakes agents keep repeating in a repo and make each one impossible: architecture first, then types, then a lint/CI check whose error names the fix, then a test, docs last. Prove each check fails on a real past mistake. Use for /correct or after a repeated correction."
---

# Correct

Adapted from pstack `correct` (MIT, Lauren Tan).

Assume every contributor is an agent that sees only the files it opened, copies
the nearest example and takes the shortest path that compiles. Make a change that
looks right from one file right for the whole repo.

## Find mistake classes

Read recent commits, reverts, follow-up fixes, the user's PR review comments,
bot findings that led to fixes, agent instruction files and workaround comments.
Use `recall` for the user's transcript corrections. A class counts once it has
happened twice; cite each occurrence.

## Fix each class at the highest level that works

1. **Architecture.** One owner per piece of state, one supported way per task.
   Hide internals so the wrong import fails. Replace hand-synced lists with one
   source of truth. Delete legacy paths an agent would copy.
2. **Types**, so the bad state can't be written. If bad code still compiles, add a
   lint or CI check whose error names the file, type or function to use instead.
   If the pattern is already common, fail only on additions.
3. **Tests** of behavior. Fix or delete tests that pass when behavior breaks.
4. **Docs or agent rules last**, only for judgment calls.

## Prove

Prove each new check fails on a real past mistake (revert-apply the old diff or
replay it in a fixture). Run the same command locally and in CI. Exceptions go on
the offending line with a reason.

Keep a rule table in the agent instruction file pairing each rule with its
enforcer. A repeated correction for a documented but unenforced rule must be
fixed at a higher level in the same change.

**Reply:** each class with evidence and counts, the level chosen, and why a
higher level didn't work. Respect the checkpoint: a plan request changes no code.

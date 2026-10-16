---
name: sharpen
description: "Sharpen a task before starting: restate the user's goal in your own words, the expert approach, and the right level of specification, then confirm. Use for /sharpen, /in-your-own-words, or 'confirm this prompt with me'."
---

# Sharpen

Adapted from pstack `sharpen` and `in-your-own-words` (MIT, Lauren Tan).

Before starting, work out:

- What the user is really after: the problem behind the request, in your own words.
- How a top expert would do it: their raw sources, their real methods, and one
  outside check that the result is right.
- Whether the task is over- or underspecified. Loosen constraints that don't
  serve the goal as readily as you add ones that do. Leave choices that are the
  user's to make open.

Fold in only what makes the work better, not bigger. Always keep the outside check.

If the user asked to confirm, reply with the restated goal, the approach, the
done predicate, and what is out of scope. Use `AskUserQuestion` only for genuine
forks the code can't answer, then stop. Otherwise do the work without narrating
the framing. Don't hand back a rewritten prompt.

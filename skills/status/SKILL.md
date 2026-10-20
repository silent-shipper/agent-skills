---
name: status
description: "Catch the user up on what changed in this chat since their last message, in plain words and small visuals, and list every item waiting on them with what they need to decide it from the reply alone. Use for /status, 'where are we', 'catch me up' within this conversation, the end of a plan, implementation or PR review, and the final reply of a long or unattended run."
---

# Status

Adapted from pstack `ketchup` and `bro` (MIT, Lauren Tan).

Catch the user up on what changed since the last message they wrote, and help
them understand each change, not only where it stands. Then lay out every call
waiting on them so they can make it from this reply alone. Notifications and
subagent results are not their messages. Assume the user remembers their last
message and nothing after it. Past sessions and other threads belong to `recall`.

Write plainly, like one person catching up another: short sentences, no jargon.
Say what changed for the user, not how you did it. Say "the tests pass", not
"CI is green". Leave out hashes, file paths, commands and build numbers unless
the user needs one to act. Call each PR, branch or agent by a name the user
would know. If a fact needs context to make sense, give the context or leave
the fact out. When the user asks for simple, ADHD-friendly or
mental-model-first communication, open with one concrete before/after or a
three-step flow.

## Gather what changed

Keep this step read-only. Make visuals only from what you already have; do not
change code, start an app or job, or post anything. Collect your own work since
that message, subagent reports, and messages from anyone else in the chat. Check
the current state of each PR, CI run or agent this chat touched. Check each
number you will show against its source, and say so when you correct one.

An action item is a call or step only the user can take: a product choice, an
approval, an irreversible action, or access you lack. Include any still waiting,
even one raised before their last message. Work you can still do yourself is not
an action item. Never make up a call to fill the reply. For each item, collect
its link, what it changes for users, the evidence behind your pick, its risk and
your pick. Write "unknown" for a fact the call needs that you do not know.

## Write the reply

Spend words on the calls, not the story. Keep what happened under 100 words,
not counting pictures, and shorter when less happened. Give each action item
about 30 words. Never cut or shrink items to stay under a word count: no count
in place of a list, no link in place of an item.

1. Open with one short sentence giving the outcome and naming what waits on
   the user, or saying nothing does. If nothing happened and nothing waits,
   say so and stop.
2. Show what happened, pictures first: screenshots and videos the work
   produced, then any diagram that explains a change.
3. One short bullet per thing the user asked for: what came of it, why it is
   worth having, and whether it is done and checked (say how, in plain words),
   failed, still running, or not checked. Write each line the way you would
   say it out loud, and keep it true when read alone. Name any bug found and
   fixed on the way. Never mark something done that still waits on the user.
4. At most three short lines that change what the user knows or must do, then
   one line naming work left that you can do yourself.
5. The action items. A call about one item is one bullet: the call, your pick,
   what it changes for users, the evidence and the risk. When items share a
   call, write the call and pick once, then one bullet per item, riskiest
   first. Give each item's risk even when low ("Low risk: only the colors
   change."). For a call between options, give each option's gain and cost.
6. For completed changes, end with `Files: N total — T tests, C code` from the
   actual diff. For a plan, label it `Files (estimated): ~N total — ~T tests,
   ~C code`. Count every non-test file as code.

## Visuals

A visual is a picture: a screenshot, a video, a Mermaid diagram, or a rendered
chart or diagram page. A Markdown table is not a visual.

Draw when something is easier to grasp as a picture: how a design works, a PR
stack with each PR's state, a before and after, or options side by side. Never
draw a status list, a list of action items, or boxes with nothing connecting
them. Keep each visual to at most six boxes of at most eight words, labeled in
plain words. Embed screenshots inline when the change is visible; if a visible
change has none, mark its line "No screenshot yet" and say what changed on
screen. Never invent a number, never draw a screen you did not capture, and
link only artifacts that exist.

# Bug fix

**You own the diagnosis.** Every shipped line traces to runtime evidence. A
change that "might help" is a hypothesis, not a fix; revert what a refuted
hypothesis motivated. The smallest change the evidence justifies ships.

1. Reproduce it yourself on the surface where it was reported:
   `create-verification` for supported Defuse work, otherwise the app's real
   run path. Ask the user only for a specific reason you cannot reach the
   target, after driving it as far as it goes. If it will not fire, synthesize
   the trigger, tighten conditions or add instrumentation until it does.
2. Narrow the cause. Seed hypotheses with `how` over the affected subsystem, and
   with `why` when the bug may be a regression or the code looks deliberate.
   Each pass, take the check that rules out the most, read real state instead
   of guessing, and eliminate. Apply **Fix root
   causes**; after two failed fixes on one premise, apply **Attack the
   premise**. Confirm the surviving mechanism with runtime evidence.
3. Plan the fix. If it crosses a module boundary, run `architect` first. When
   delegating, give the subagent the mechanism, file paths and success criteria.
4. Verify on the same surface: the original repro now passes. Inconclusive or
   wrong-surface is not a pass; say so. Unit tests show branch behavior, not
   bug absence.
5. Add regression coverage when there is a cheap local test path (**Test
   behavior, not implementation**), and show it failing without the fix and
   passing with it. Skip with a reason when the test would be expensive or
   unclear.
6. Ship with `ship` when authorized; otherwise stop at the local checkpoint.

**Reply:** what was broken, the root cause, the fix, and the failing-then-passing
proof.

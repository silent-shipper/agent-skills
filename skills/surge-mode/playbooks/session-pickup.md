# Session pickup

**You own the resume point.** The prior trail is authoritative input; read it
instead of redoing it.

1. Locate the prior trail: this project's transcripts (`recall` finds them),
   the T3 thread (`t3_thread_search` and `t3_thread_read`), a pushed branch or
   PR, or a `show-me-your-work` log. Stay within the current project's
   history. Parse a long transcript in a subagent and keep the reduced timeline
   here (**Guard the context window**).
2. Reconstruct operational state: branch and worktree, what already landed
   (`git log` and `git diff` against the base), open todos and decisions made.
3. Diff done against pending and name the resume point. Do not re-run a prior
   repro or redo completed work without a concrete reason to doubt it.
4. Route the remaining work to its playbook, and say whether you continue,
   ship a finished result, ratify or override a prior conclusion, or
   postmortem a failed run.
5. Verify the inherited claims the outcome depends on against the real
   artifact. A prior agent's "done" is not proof, but recorded evidence for the
   current head is; rerun an expensive check only when that evidence is missing
   or stale. Prior shipping authorization carries over only when the trail
   shows the user granting it for this scope.

**Reply:** where the prior work stopped, what you inherited versus redid, the
resume point and the outcome.

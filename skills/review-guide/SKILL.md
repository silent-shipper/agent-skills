---
name: review-guide
description: Build a Capy-style guided review of a PR, branch or working-tree change, rendered as a standalone HTML page with an Overview, a Before / after view, and bite-sized chapters that pair a plain-language explanation with the code they cover. Use when the user says "review guide", "$review-guide", "/review-guide", "guide this PR", "guided review", or asks for a code tour of a change.
---

# Review guide

Produce the page Capy calls a **Guide**: a reading order for a change, not a summary sitting on top of a diff. The reader
should understand what the system did before, what changed and why, chapter by chapter, with the code beside each
explanation. The renderer reproduces Capy's layout exactly; your job is the content.

`SCRIPT=<this skill's directory>/scripts/review_guide.py`

## 1. Collect

Run inside the repository:

- PR: `python3 $SCRIPT collect --pr <number|url>` (uses `gh`, fetches the head if needed)
- Branch: `python3 $SCRIPT collect --head <ref>` (uses the branch's open PR, if any, for base, title and
  description; `--base <ref>` overrides the base and collect warns when that no longer matches the PR)
- Current work: `python3 $SCRIPT collect` (merge-base with the default branch → working tree, uncommitted included)

It prints every changed file with counts, a suggested label (`tests`, `database`, `generated`) and detected moved blocks,
and writes `diff.json` and `diff.patch` to `<git-dir>/review-guides/<pr-or-branch>/` (or `--out <dir>`); from a worktree
that is the main checkout's shared git dir, so every worktree sees the same guides. Use the
`Write:` and `Then:` paths it prints. It warns when uncommitted or untracked work is left out; mention it if it matters.

**New push on a change that already has a guide:** collect again into the same directory. It reports which files are new,
gone or changed since the guide was rendered and writes `since-guide.patch` with exactly what changed in them. It also lists
Before / after `at` targets whose line moved. Read the patch, then update the chapters, overview steps and Before /
after lines (and those `at` targets) the changes make wrong or incomplete, and fix any
other statement you find false (for example, a chapter about a file that is now deleted). Keep everything else as it
is, then do steps 4–5. If it reports that the guide still matches, render it and do step 4's reread only.

## 2. Understand the change

Read all of `diff.patch` (it already leaves out generated, deleted and binary files); page through it using each file's
`@N` start line from collect's listing. Open the surrounding code until you
can say, concretely, what the system did **before** and what it does **after**: entry points, callers, data shape,
decisions. Read the PR description and linked issue if there is one. Do not write chapters from file names.

## 3. Write `guide.json`

Write it at the `Write:` path. Follow `references/writing.md` exactly; it holds the schema, Capy's voice and structure rules,
and a full example. The non-negotiables:

- **Overview**: one or two sentences (the problem as it was, or what the change adds and why), then 2–5 short steps.
- **Before / after**: a behavior-level call tree (a flow diagram only under the strict rules in writing.md) of the one
  path that changed, with `-` for the
  old behavior, `+` for the new, and each line pointing at the chapter that implements it. Not code; not a file list.
- **Chapters**: in reading order (cause before effect, core before callers before plumbing), never file-tree order.
  Bite-sized: usually 1–3 files, one idea each. Every changed file appears in exactly one chapter.
- Tests stay out of the guide: no test chapters, no test files in chapters (they remain in the Diff tab).
- Database migrations and generated files go in labelled chapters at the end. Lockfiles and generated files are named,
  not explained. `database` and `generated` labels are hints from paths; override them when the content says otherwise.

## 4. Render and check

`python3 $SCRIPT render <dir>` validates the guide (every non-test file covered once, no test files, refs valid, diagram limits, labelled chapters
last) and writes
`review-guide.html`; success starts with `Validated:`. Fix every reported problem and render again. Then reread the Overview and the first chapter as a
reviewer who has never seen the code: if either needs the diff to make sense, rewrite it.

## 5. Show it

Publish the HTML with `html_render` when that tool is available; otherwise `open <dir>/review-guide.html`. Reply with
the path, the chapter list (one line each) and what the guide could not verify: work left out (uncommitted, untracked),
intent inferred from commits rather than stated, and behavior you described without running it. Do not repeat the
guide's content.

## Every push

Capy writes a guide on every push. To do the same, run `python3 $SCRIPT pending` inside the repository (`--author` to
change whose PRs; default `@me`). For each PR it lists, run steps 1–5 with `--pr <number>`; "push a → b" means update
the existing guide as described in step 1, "no guide yet" means write one. In these runs, skip opening pages; publish with `html_render` only when that tool
is available, and reply with one line per PR: number, written or updated, path. If it lists nothing, stop. For hands-off use,
schedule a recurring run whose prompt is `$review-guide pending in <repository path>`.

The page is self-contained and works offline (avatars aside) and fills wide screens. Reviewed checkboxes persist per change in the browser. `rendered.json` records what the guide was rendered from, for the
update check in step 1, and the
render before it: after a push, files and chapters that changed since that render show "updated since <sha>", and a
file's Reviewed tick holds only while its diff is unchanged, so the reader re-reviews just what moved.

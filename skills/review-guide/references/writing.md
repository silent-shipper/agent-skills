# Writing a guide

Capy's guides exist because nobody reads a diff in file-tree order. A guide earns its place only if a reviewer who
reads it top to bottom understands the change faster than they would from the diff. Write for that reviewer.

## Schema

```json
{
  "title": "optional; defaults to the PR title, else the only commit's subject, else the branch name",
  "overview": {
    "summary": "One or two sentences. `backticks` render as code chips.",
    "steps": ["2–5 short steps the change takes"],
    "before_after": [ { "caption": "...", "lines": [ ... ] } ]
  },
  "chapters": [
    { "title": "...", "summary": "Paragraph.\n\nOptional second paragraph.", "files": ["exact/path/from/diff.json"],
      "label": "database | generated (optional)" }
  ]
}
```

`before_after` is one block or a list of blocks. A block may set `label`, a muted word after "Before / after" naming
the view ("call tree", "flow"); usually omit it. Two kinds:

- **Tree** (default). `lines`: `{ "op": "-" | "+" (omit for context), "depth": 0.., "text": "...", "note": "muted aside",
  "ref": 3, "at": "load-blob.ts:42" }`. An integer `ref` renders as a boxed `03` linking to that chapter. `at` renders as
  a muted `load-blob.ts 42` that opens that exact line of the diff and highlights it; a `+` line must name an added line
  (new numbering), a `-` line a removed line (old numbering), and a context line any line on the new side; render
  rejects anything else. The file part may be
  any unique path suffix. The card header counts `+` and `-` lines.
- **Diagram** (rare): `{ "kind": "diagram", "caption": "...", "nodes": [ { "id": "a", "text": "takeShare()", "type":
  "new | removed | decision | plain", "tag": "optional, e.g. New · step.ts", "ref": 1, "at": "optional file:line" } ], "rows": [["a", "b"], ["c"]],
  "edges": [ { "from": "b", "to": "c", "label": "files" } ] }`. `rows` place nodes on a grid of lanes (`null` leaves a
  cell empty); the page draws rounded wires that wrap from the end of one row to the start of the next. Without a `tag`,
  new and removed nodes render as one line with a `+` / `−` and a tinted fill, like Capy's launch demo.

## How Capy writes them

Capy's published guides, verbatim:

> **Retry blob reads with backoff instead of caching failures**
> Overview: "A single failed blob read used to stick in the session cache, so one network blip broke every diff that
> touched that file until a reload." Steps: "Reads go through `withRetry`, which backs off and tries again before
> giving up." · "The blob cache is gone, so nothing replays an old failure." · "Patch text is rebuilt from the fresh
> read, and the docs describe the retry policy."
> Before / after, "How a blob read reaches the network":
> ```
>   loadBlob(path)
> -   blobCache.get(path)                  a cached failure was returned for the rest of the session   01
> +   withRetry(() => fetchBlob(path))     backs off and tries again on a network error                01
>       fetchBlob(path)
> +   patchText(previous, next)            built from the fresh read                                   02
>     manifest.record(path, attempt)
> ```

> **feat(mobile): share extension and Android share intent to a new or existing thread**
> Overview: "This PR adds mobile sharing so external content can be staged, uploaded, and sent to Capy threads on iOS
> and Android." Steps: "Prebuild the signed `CapyShareExtension` and register Android share intents." · "Stage shared
> items and stream them through `CapyShare`." · "Load shared session/context, choose a destination, then send." ·
> "Use the Tailnet relay when an iPhone is unavailable."
> Chapter "Send content to a destination": "The share sheet combines staged text and files with a selected project,
> thread, or Captain destination. It presigns eligible files, reports upload progress, then creates or posts to the
> chosen thread. ¶ Empty, oversized, and cumulative-over-limit files are excluded before sending, so only accepted file
> references reach the thread request."
> Chapter "Reach iPhones over Tailnet": "The device installer starts a Bonjour and TCP relay when the selected iPhone is
> unavailable, and the relay can capture and reuse its RemotePairing advertisement. ¶ The relay stops advertising when
> the phone is reachable on the LAN, so normal local pairing keeps its direct connection."

Match that voice: plain, concrete, present tense, the domain's own words, real identifiers in backticks. Never
"robust", "seamless", "comprehensive", "enhance", "leverage", "streamline", "various", "ensures that", "In order to".
Do not hedge about intent you can read from the code; if something is genuinely unclear, say exactly what.

## Guide title

Set `title` yourself when the default is a branch name or a merge commit, or when the guide covers more than the PR it
borrowed the title from. Write it like a good PR title.

## Overview

- `summary`: one sentence, two at most. Either the problem as it was ("A single failed blob read used to stick…") or
  what the PR adds and why ("This PR adds mobile sharing so…"). Not a list of files.
- `steps`: 2–5 short steps in the order the change works, each one line where possible, often imperative ("Stage
  shared items and stream them through `CapyShare`."). Omit for single-idea changes.

## Before / after

- `caption` names the path being shown, not the change: "How a blob read reaches the network", "Shared content reaches
  a thread", "Merge action on a Ready to merge row".
- The tree is that path in execution order, nested by who calls whom (`depth`). Each line is a real call or step from
  the code (`withRetry(() => fetchBlob(path))`); when the change is a rule inside one place, a line may be a condition
  and its outcome (`any check failed → "Merge blocked on red CI", disabled`).
- `-` lines are what the old path did; `+` lines are what it does now. Unchanged calls stay as context so the reader
  sees where the change sits.
- Put the meaning in `note`, in plain words, on the changed lines ("a cached failure was returned for the rest of the
  session"). Every `+` and `-` line gets the `ref` of the chapter where that behavior is decided (not merely called)
  and an `at` pointing at the line that does it, so a click opens that code.
- 4–12 lines. If it needs more, the path is too broad; show the one a reviewer most needs.

**Default to the tree**; a weak diagram is worse than none. Draw a diagram only when all of these hold:

- The change creates or reroutes a path through several functions and it branches (a reader must follow two outcomes).
- 4–8 nodes, at most 4 rows of at most 4 nodes, node text 44 characters or less (render rejects more).
- Every node is a real call or decision from the code. New ones `"type": "new"`, deleted ones `"removed"`, branch points
  `"decision"` with a question as text.
- Rows follow reading order: the main path left to right, wrapping down; each branch outcome in its own lane (one beside
  the branch point, one below it). Label only branch edges, with a one-word outcome (`yes`, `no`, `files`, `thread`).

## Chapters

- **Order**: the order a person would explain the change at a whiteboard. The core change first, then what uses it,
  then wiring, configuration and cleanup. Moved code goes in the chapter of the idea that moved it.
- **One idea per chapter.** A chapter may hold one file or seven, as long as they serve the same idea. Files cannot be
  split: put each file where most of its change belongs and mention its other edits in that chapter's summary.
- **Title**: a short phrase naming the behavior, a verb phrase or a noun phrase: "Stage and upload shared files",
  "Reach iPhones over Tailnet", "Merge gate on the board". Not "Update X", not a file name, not "Refactor".
- **Summary**: one paragraph of 1–2 sentences on what this code does, naming the key identifiers. Add a second paragraph
  (separate with a blank line) only for the consequence or edge case a reviewer must not miss, usually a "so …"
  sentence. About 80 words at most; leave formulas and option lists to the code beside it.
- **Tests are not in the guide.** Leave every file collect tags `tests` out of the chapters (render rejects them); they
  stay in the Diff tab, and the Overview links there. Do not mention tests in the Overview or Before / after. A test
  helper collect did not tag still needs a chapter: give it to the one it supports, in one short clause.
- **Labelled chapters** come last, in this order when present: `database`, `generated`.
  - `database`: migrations and schema. Say what the schema gains or loses and whether existing rows change.
  - `generated`: lockfiles, snapshots, codegen. One sentence naming what regenerated it. These render collapsed.
- Pure renames and import-path churn across many files: one chapter, summarized by pattern ("Every caller imports from
  the colocated paths").

## Example

```json
{
  "overview": {
    "summary": "A single failed blob read used to stick in the session cache, so one network blip broke every diff that touched that file until a reload.",
    "steps": [
      "Reads go through `withRetry`, which backs off and tries again before giving up.",
      "The blob cache is gone, so nothing replays an old failure.",
      "Patch text is rebuilt from the fresh read, and the docs describe the retry policy."
    ],
    "before_after": {
      "caption": "How a blob read reaches the network",
      "lines": [
        { "text": "loadBlob(path)" },
        { "op": "-", "depth": 1, "text": "blobCache.get(path)", "note": "a cached failure was returned for the rest of the session", "ref": 1, "at": "load-blob.ts:18" },
        { "op": "+", "depth": 1, "text": "withRetry(() => fetchBlob(path))", "note": "backs off and tries again on a network error", "ref": 1, "at": "load-blob.ts:21" },
        { "depth": 2, "text": "fetchBlob(path)" },
        { "op": "+", "depth": 1, "text": "patchText(previous, next)", "note": "built from the fresh read", "ref": 2, "at": "patch-text.ts:9" },
        { "depth": 1, "text": "manifest.record(path, attempt)" }
      ]
    }
  },
  "chapters": [
    {
      "title": "Retry blob reads with backoff",
      "summary": "`loadBlob` now calls `fetchBlob` through `withRetry`, which waits longer after each network error and gives up after the last attempt.\n\nThe session `blobCache` is removed, so a failed read is never served again from memory.",
      "files": ["packages/web/src/diff/load-blob.ts", "packages/web/src/lib/with-retry.ts"]
    },
    {
      "title": "Patch text from the fresh read",
      "summary": "`patchText` builds the patch from the blob just fetched instead of the cached copy, and the docs describe the retry policy.",
      "files": ["packages/web/src/diff/patch-text.ts", "docs/diffs.md"]
    }
  ]
}
```

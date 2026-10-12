#!/usr/bin/env python3
"""Collect a change and render it as a Capy-style guided review page."""
import argparse
import html
import json
import re
import subprocess
import sys
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"
LABELS = ("database", "generated")
LOCKFILES = {
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lock", "bun.lockb", "cargo.lock",
    "poetry.lock", "uv.lock", "go.sum", "gemfile.lock", "composer.lock", "flake.lock", "pipfile.lock",
}
GENERATED = re.compile(
    r"(^|/)(generated|__generated__|dist|build|vendor)/|\.(gen|generated|pb|min)\.[a-z]+$|_pb2\.py$|\.snap$"
)
TESTS = re.compile(r"(^|/)(tests?|__tests__|__mocks__|specs?|e2e|fixtures|playwright|cypress|testing|test-utils)/"
                   r"|\.(test|spec|e2e|stories)\.[a-z]+$|_test\.(go|py|rb)$|(^|/)test_[^/]*\.py$|(^|/)conftest\.py$")
DATABASE = re.compile(r"(^|/)(migrations?|db/schema)|\.sql$|schema\.prisma$|(^|/)drizzle/")


def run(*args, check=True):
    result = subprocess.run(args, capture_output=True, text=True, errors="replace")
    if check and result.returncode:
        raise SystemExit(f"{' '.join(args)} failed:\n{result.stderr.strip()}")
    return result.stdout


def git(*args, check=True):
    return run("git", *args, check=check)


# ---------------------------------------------------------------- collect


def default_base():
    ref = git("rev-parse", "--abbrev-ref", "origin/HEAD", check=False).strip()
    for candidate in (ref, "origin/main", "origin/master", "main", "master"):
        if candidate and git("rev-parse", "--verify", "--quiet", candidate, check=False).strip():
            return candidate
    raise SystemExit("Could not find a base branch; pass --base.")


PR_FIELDS = "number,title,body,url,author,createdAt,baseRefName,headRefName,headRefOid"


def pr_meta(info):
    return {
        "title": info["title"], "number": info["number"], "url": info["url"], "body": info["body"],
        "author": info["author"].get("name") or info["author"]["login"], "login": info["author"]["login"],
        "created_at": info["createdAt"], "base_ref": info["baseRefName"], "head_ref": info["headRefName"],
    }


def branch_pr(branch):
    """The open PR for a local branch, when gh can find one."""
    if branch == "HEAD":
        return None
    try:
        result = subprocess.run(["gh", "pr", "view", branch, "--json", PR_FIELDS], capture_output=True, text=True)
    except FileNotFoundError:
        return None
    return json.loads(result.stdout) if result.returncode == 0 else None


def resolve(args):
    if args.pr:
        info = json.loads(run("gh", "pr", "view", args.pr, "--json", PR_FIELDS))
        head = info["headRefOid"]
        git("fetch", "--quiet", "origin", info["baseRefName"], check=False)
        if subprocess.run(["git", "cat-file", "-e", head + "^{commit}"], capture_output=True).returncode:
            git("fetch", "--quiet", "origin", f"pull/{info['number']}/head")
        base = git("merge-base", "origin/" + info["baseRefName"], head).strip()
        return base, head, pr_meta(info)
    branch = git("rev-parse", "--abbrev-ref", args.head or "HEAD").strip()
    info = branch_pr(branch)
    pr_base = info and "origin/" + info["baseRefName"]
    head, base_ref = args.head, args.base or pr_base or default_base()
    head = head and git("rev-parse", "--verify", head + "^{commit}").strip()
    base = git("merge-base", base_ref, head or "HEAD").strip()
    tip = head or "HEAD"
    subjects = git("log", "--format=%s", f"{base}..{tip}").strip().splitlines()
    meta = {
        "title": subjects[0] if len(subjects) == 1 or branch == "HEAD" and subjects else branch,
        "number": None, "url": None,
        "body": git("log", "--reverse", "--format=%s%n%n%b", f"{base}..{tip}").strip(),
        "author": git("config", "user.name", check=False).strip() or "You", "login": None,
        "created_at": git("log", "-1", "--format=%cI", tip).strip(), "base_ref": base_ref,
        "head_ref": branch if head else branch + " (working tree)",
    }
    if info and base_ref.removeprefix("origin/") == info["baseRefName"]:
        meta.update({key: value for key, value in pr_meta(info).items() if key not in ("base_ref", "head_ref")})
    elif info:
        meta["pr_mismatch"] = f"PR #{info['number']} targets {info['baseRefName']}, so its title and description cover " \
                              f"less than this diff. Use --pr {info['number']} to guide only the PR."
    return base, head, meta


def parse_patch(patch):
    files, current, hunk = [], None, None
    for line in patch.split("\n"):
        if line.startswith("diff --git "):
            match = re.match(r'diff --git "?a/(.*?)"? "?b/(.*?)"?$', line)
            current = {"path": match[2], "old_path": match[1], "status": "modified", "binary": False,
                       "additions": 0, "deletions": 0, "hunks": []}
            files.append(current)
            hunk = None
        elif current is None:
            continue
        elif hunk is not None and line and line[0] in " +-\\":
            if line[0] == "\\":
                continue
            kind, text = line[0], line[1:]
            entry = {"t": kind, "s": text}
            if kind != "+":
                entry["o"] = hunk["o"]
                hunk["o"] += 1
            if kind != "-":
                entry["n"] = hunk["n"]
                hunk["n"] += 1
            if kind == "+":
                current["additions"] += 1
            elif kind == "-":
                current["deletions"] += 1
            hunk["lines"].append(entry)
        elif line.startswith("@@"):
            match = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
            hunk = {"old_start": int(match[1]), "new_start": int(match[3]),
                    "o": int(match[1]), "n": int(match[3]), "lines": []}
            current["hunks"].append(hunk)
        elif line.startswith("new file"):
            current["status"] = "added"
        elif line.startswith("deleted file"):
            current["status"] = "deleted"
        elif line.startswith("rename from "):
            current["status"], current["old_path"] = "renamed", line[12:]
        elif line.startswith("rename to "):
            current["path"] = line[10:]
        elif line.startswith("Binary files"):
            current["binary"] = True
    for file in files:
        for hunk in file["hunks"]:
            hunk.pop("o"), hunk.pop("n")
    return files


def suggest_label(file):
    path = file["path"].lower()
    head = "\n".join(line["s"] for hunk in file["hunks"][:1] for line in hunk["lines"][:8])
    if path.rsplit("/", 1)[-1] in LOCKFILES or GENERATED.search(path) or "@generated" in head or "DO NOT EDIT" in head:
        return "generated"
    if TESTS.search(path):
        return "tests"
    if DATABASE.search(path):
        return "database"
    return None


def significant(text):
    return len(re.sub(r"\W", "", text)) >= 2


def detect_moves(files, min_lines=4):
    """Mark blocks of deleted lines that reappear verbatim as added lines elsewhere."""
    def runs(kind):
        for fi, file in enumerate(files):
            for hi, hunk in enumerate(file["hunks"]):
                start = None
                for li, line in enumerate(hunk["lines"] + [{"t": "end"}]):
                    if line["t"] == kind and start is None:
                        start = li
                    elif line["t"] != kind and start is not None:
                        yield fi, hi, start, li
                        start = None

    if sum(f["additions"] + f["deletions"] for f in files) > 40000:
        return
    added = {}
    for fi, hi, start, end in runs("+"):
        for li in range(start, end):
            key = files[fi]["hunks"][hi]["lines"][li]["s"].strip()
            if significant(key):
                added.setdefault(key, []).append((fi, hi, li, end))
    taken = set()
    for fi, hi, start, end in runs("-"):
        deleted = files[fi]["hunks"][hi]["lines"]
        li = start
        while li < end:
            best = None
            for afi, ahi, ali, aend in added.get(deleted[li]["s"].strip(), ()):
                if (afi, ahi) == (fi, hi) or (afi, ahi, ali) in taken:
                    continue
                target = files[afi]["hunks"][ahi]["lines"]
                length = 0
                while li + length < end and ali + length < aend and (afi, ahi, ali + length) not in taken \
                        and deleted[li + length]["s"].strip() == target[ali + length]["s"].strip():
                    length += 1
                weight = sum(significant(deleted[li + k]["s"]) for k in range(length))
                if weight >= min_lines and (best is None or length > best[3]):
                    best = (afi, ahi, ali, length)
            if not best:
                li += 1
                continue
            afi, ahi, ali, length = best
            target = files[afi]["hunks"][ahi]["lines"]
            for k in range(length):
                taken.add((afi, ahi, ali + k))
                deleted[li + k]["mv"] = target[ali + k]["mv"] = 1
            deleted[li]["move"] = {"dir": "to", "path": files[afi]["path"], "count": length}
            target[ali]["move"] = {"dir": "from", "path": files[fi]["path"], "count": length}
            li += length


def fingerprint(file):
    return json.dumps([[line["t"], line["s"]] for hunk in file["hunks"] for line in hunk["lines"]])


def patch_sections(patch):
    sections = {}
    for chunk in re.split(r"(?m)^(?=diff --git )", patch):
        match = re.match(r'diff --git "?a/.*? "?b/(.*?)"?\n', chunk)
        if match:
            sections[match[1]] = chunk
    return sections


def write_since(out, previous, head, paths):
    """Write what changed in `paths` since the guide was rendered: the pushed commits, else a diff of the two patches."""
    old = previous.get("head")
    commits = [h for h in (old, head) if h and h != "WORKTREE"]
    if len(commits) == 2 and all(subprocess.run(["git", "cat-file", "-e", h + "^{commit}"], capture_output=True).returncode == 0
                                 for h in commits):
        text = git("diff", "--no-color", "-M", "-U5", old, head, "--", *paths)
    else:
        import difflib
        before = patch_sections((out / "rendered.patch").read_text()) if (out / "rendered.patch").exists() else {}
        after = patch_sections((out / "diff.patch").read_text())
        text = "".join("".join(difflib.unified_diff(before.get(path, "").splitlines(True), after.get(path, "").splitlines(True),
                                                    f"guide/{path}.patch", f"now/{path}.patch")) for path in paths)
    (out / "since-guide.patch").write_text(text)
    return bool(text.strip())


def report_update(previous, files, guide, out, head):
    """Compare a new collection with the one an existing guide was written for."""
    before = previous["files"]
    guided = {path for chapter in guide.get("chapters", []) for path in chapter.get("files", [])}
    current = {f["path"]: fingerprint(f) for f in files}
    new = sorted(path for path in current if path not in guided)
    gone = sorted(path for path in guided if path not in current)
    changed = sorted(path for path in current if path in guided and before.get(path) != current[path])
    old_head = short(previous.get("head"))
    if not (new or gone or changed):
        print(f"\nExisting guide written for {old_head} still matches every file. Render it again as is.")
        return
    print(f"\nExisting guide was written for {old_head}. Update guide.json instead of rewriting it:")
    for title, paths in (("New, not in any chapter", new), ("Gone, remove from chapters", gone),
                         ("Changed since the guide was written", changed)):
        if paths:
            print(f"  {title}:\n    " + "\n    ".join(paths))
    if write_since(out, previous, head, sorted(set(new + changed))):
        print(f"  What changed since the guide: {out / 'since-guide.patch'}")


def short(head):
    return "working tree" if head in (None, "WORKTREE") else head[:7]


def collect(args):
    if git("rev-parse", "--is-inside-work-tree", check=False).strip() != "true":
        raise SystemExit("Run collect inside the repository you want to review.")
    base, head, meta = resolve(args)
    revs = [base] + ([head] if head else [])
    common = ["diff", "--no-color", "--no-ext-diff", "-M", "--src-prefix=a/", "--dst-prefix=b/"]
    files = parse_patch(git(*common, "--function-context", *revs))
    if not files:
        raise SystemExit(f"No changes between {meta['base_ref']} and {meta['head_ref']}.")
    for file in files:
        file["label"] = suggest_label(file)
    detect_moves(files)
    meta.update(base=base, head=head or "WORKTREE", repo=Path(git("rev-parse", "--show-toplevel").strip()).name)

    slug = str(meta["number"]) if meta["number"] else re.sub(r"[^\w.-]+", "-", meta["head_ref"]).strip("-")
    common_dir = Path(git("rev-parse", "--path-format=absolute", "--git-common-dir").strip())
    out = Path(args.out) if args.out else common_dir / "review-guides" / slug
    out.mkdir(parents=True, exist_ok=True)
    snapshot = out / "rendered.json"
    previous = json.loads(snapshot.read_text()) if snapshot.exists() else None
    (out / "diff.json").write_text(json.dumps({"meta": meta, "files": files}))

    readable = sorted({path for f in files if f["label"] != "generated" and f["status"] != "deleted" and not f["binary"]
                       for path in (f["path"], f["old_path"])})
    patch = git(*common, "-U8", *revs, "--", *readable) if readable else ""
    (out / "diff.patch").write_text(patch)
    starts = {}
    for number, line in enumerate(patch.split("\n"), 1):
        match = re.match(r'diff --git "?a/.*? "?b/(.*?)"?$', line)
        if match:
            starts[match[1]] = number

    untracked = git("ls-files", "--others", "--exclude-standard").split() if not head and not args.pr else []
    dirty = git("status", "--porcelain").strip() if head and not args.pr else ""
    print(f"{meta['title']}  ({meta['base_ref']} ← {meta['head_ref']})")
    print(f"{len(files)} files  +{sum(f['additions'] for f in files)} -{sum(f['deletions'] for f in files)}\n")
    for file in files:
        label = "tests · Diff tab only" if file["label"] == "tests" else file["label"]
        tags = " ".join(t for t in (label, "binary" if file["binary"] else None) if t)
        moved = sum(1 for h in file["hunks"] for line in h["lines"] if "move" in line)
        moves = f"  ({moved} moved block{'s' if moved > 1 else ''})" if moved else ""
        at = f"  @{starts[file['path']]}" if file["path"] in starts else ""
        print(f"  {'+' + str(file['additions']):>6} {'-' + str(file['deletions']):>6}  {file['status']:<8} "
              f"{file['path']}{'  [' + tags + ']' if tags else ''}{moves}{at}")
    if meta.get("pr_mismatch"):
        print("\n" + meta.pop("pr_mismatch"))
    elif meta["number"] and not args.pr:
        print(f"\nFound PR #{meta['number']} for this branch; using its title and description.")
    if dirty:
        print("\nNot included: uncommitted changes in the working tree (omit --head to include them).")
    if untracked:
        print(f"\nNot included (untracked): {', '.join(untracked[:10])}{' …' if len(untracked) > 10 else ''}")
    if previous and (out / "guide.json").exists():
        report_update(previous, files, json.loads((out / "guide.json").read_text()), out, meta["head"])
    print(f"\nRead:  {out / 'diff.patch'}  (@N = the file's first line in it; generated, deleted and binary files are left out)")
    print(f"Write: {out / 'guide.json'}")
    print(f"Then:  python3 {Path(__file__).resolve()} render {out}")


# ---------------------------------------------------------------- render

KEYWORDS = set("""
abstract as async await break case catch class const continue debugger def default defer del delete do elif else
enum except export extends final finally fn for from func function go if impl implements import in instanceof
interface is lambda let loop match mod module mut new not of or and package pass private protected pub public raise
readonly return satisfies select static struct super switch throw trait try type typeof use var where while with
yield declare keyof infer namespace override get set unsafe crate self Self where
SELECT FROM WHERE INSERT INTO UPDATE DELETE CREATE TABLE ALTER ADD DROP INDEX ON JOIN LEFT RIGHT INNER OUTER AND OR NOT
NULL PRIMARY KEY REFERENCES DEFAULT VALUES SET RETURNING CONSTRAINT UNIQUE IF EXISTS COLUMN
""".split())
CONSTANTS = set("""true false null undefined None True False nil this void string number boolean any unknown never
bigint symbol object int float str bool bytes usize isize u8 u16 u32 u64 i8 i16 i32 i64 f32 f64 Ok Err Some""".split())
HASH_COMMENT = {"py", "sh", "bash", "zsh", "rb", "yml", "yaml", "toml", "pl", "r", "dockerfile", "makefile", "nix", "conf", "ini", "env"}
DASH_COMMENT = {"sql", "lua", "hs"}
TOKEN = re.compile(r"""
    (?P<str>"(?:\\.|[^"\\])*"?|'(?:\\.|[^'\\])*'?|`(?:\\.|[^`\\])*`?)
  | (?P<num>\b\d[\d_]*(?:\.\d+)?(?:[eE][+-]?\d+)?\b|\b0x[\da-fA-F]+\b)
  | (?P<id>[A-Za-z_$][\w$]*)
  | (?P<op>=>|===|!==|==|!=|<=|>=|&&|\|\||\?\?|\.\.\.|[=+\-*/%<>!?|&^~])
  | (?P<ws>\s+)
  | (?P<other>.)
""", re.X)


def ext_of(path):
    name = path.rsplit("/", 1)[-1].lower()
    return name if "." not in name else name.rsplit(".", 1)[-1]


def highlight(text, ext, state):
    """Return [(class, text)] tokens. `state` carries block-comment status across lines."""
    out = []
    if state.get("block"):
        end = text.find(state["block"])
        if end < 0:
            return [("com", text)]
        out.append(("com", text[:end + len(state["block"])]))
        text, state["block"] = text[end + len(state["block"]):], None
    comment = "#" if ext in HASH_COMMENT else "--" if ext in DASH_COMMENT else "//"
    position, previous = 0, ""
    while position < len(text):
        rest = text[position:]
        if rest.startswith(comment) and (comment != "#" or not rest.startswith("#{")):
            out.append(("com", rest))
            break
        for opener, closer in (("/*", "*/"), ('"""', '"""'), ("'''", "'''"), ("<!--", "-->")):
            if rest.startswith(opener) and (opener == "/*" or opener == "<!--" or ext == "py"):
                end = rest.find(closer, len(opener))
                if end < 0:
                    out.append(("com" if opener in ("/*", "<!--") else "str", rest))
                    state["block"] = closer
                    return out
                out.append(("com" if opener in ("/*", "<!--") else "str", rest[:end + len(closer)]))
                position += end + len(closer)
                break
        else:
            match = TOKEN.match(text, position)
            kind, value = match.lastgroup, match[0]
            if kind == "id":
                after = text[match.end():].lstrip()
                if value in KEYWORDS or value.upper() in KEYWORDS and ext == "sql":
                    kind = "kw"
                elif value in CONSTANTS:
                    kind = "con"
                elif previous == "<" and value[:1].isupper():
                    kind = "tag"
                elif after.startswith("(") or after.startswith("<") and value[:1].isupper() and previous != "<":
                    kind = "fn"
                elif value[:1].isupper():
                    kind = "ty"
                elif after.startswith(":") and not after.startswith("::") or after.startswith("?:"):
                    kind = "key"
                else:
                    kind = ""
            elif kind in ("ws", "other"):
                kind = ""
            out.append((kind, value))
            if match.lastgroup != "ws":
                previous = value if match.lastgroup in ("op", "other") else match.lastgroup
            position = match.end()
            continue
    return out


def esc(text):
    return html.escape(text, quote=True)


def code_html(text, ext, state, mark=None):
    tokens, out, offset = highlight(text, ext, state), [], 0
    for kind, value in tokens:
        pieces = [(value, False)]
        if mark:
            start, end = mark
            left, right = max(start - offset, 0), min(end - offset, len(value))
            if left < right:
                pieces = [(value[:left], False), (value[left:right], True), (value[right:], False)]
        offset += len(value)
        for piece, marked in pieces:
            if not piece:
                continue
            inner = f'<span class="t-{kind}">{esc(piece)}</span>' if kind else esc(piece)
            out.append(f"<mark>{inner}</mark>" if marked else inner)
    return "".join(out) or " "


def inline_marks(lines):
    """Character ranges that changed between paired -/+ lines."""
    marks, index = {}, 0
    while index < len(lines):
        if lines[index]["t"] != "-":
            index += 1
            continue
        start = index
        while index < len(lines) and lines[index]["t"] == "-":
            index += 1
        middle = index
        while index < len(lines) and lines[index]["t"] == "+":
            index += 1
        for a, b in zip(range(start, middle), range(middle, index)):
            old, new = lines[a]["s"], lines[b]["s"]
            if lines[a].get("mv") or old.strip() == new.strip():
                continue
            prefix = 0
            while prefix < min(len(old), len(new)) and old[prefix] == new[prefix]:
                prefix += 1
            suffix = 0
            while suffix < min(len(old), len(new)) - prefix and old[-1 - suffix] == new[-1 - suffix]:
                suffix += 1
            if prefix + suffix and (len(old) - prefix - suffix) < 0.7 * len(old) and (len(new) - prefix - suffix) < 0.7 * len(new):
                marks[a] = (prefix, len(old) - suffix)
                marks[b] = (prefix, len(new) - suffix)
    return marks


def indent(text):
    expanded = text.expandtabs(4)
    return len(expanded) - len(expanded.lstrip())


def visible_lines(lines, context=3):
    """Keep changes, nearby context and the enclosing scope lines (function, loop, block) of each change."""
    keep = set()
    for index, line in enumerate(lines):
        if line["t"] == " ":
            continue
        keep.update(range(max(index - context, 0), min(index + context + 1, len(lines))))
        if index and lines[index - 1]["t"] != " ":
            continue
        probe = index
        while probe < len(lines) and not lines[probe]["s"].strip():
            probe += 1
        level = indent(lines[probe]["s"]) if probe < len(lines) else 0
        for back in range(index - 1, -1, -1):
            text = lines[back]["s"]
            if level == 0:
                break
            if text.strip() and lines[back]["t"] == " " and indent(text) < level:
                level = indent(text)
                if text.lstrip()[0] not in ")]}":
                    keep.add(back)
                    continue
                for opener in range(back - 1, -1, -1):
                    candidate = lines[opener]["s"]
                    if candidate.strip() and indent(candidate) == level and candidate.lstrip()[0] not in ")]}":
                        keep.add(opener)
                        break
    return keep


def row(line, ext, state, mark=None):
    kind = {"+": "add", "-": "del", " ": "ctx"}[line["t"]]
    number = line.get("n") if line["t"] != "-" else line.get("o")
    moved = " moved" if line.get("mv") else ""
    out = f'<div class="r {kind}{moved}"><span class="ln">{number}</span><span class="c">{code_html(line["s"], ext, state, mark)}</span></div>'
    return out


def chip(move):
    arrow = "↗" if move["dir"] == "to" else "↙"
    label = "Moved to" if move["dir"] == "to" else "Moved from"
    return (f'<div class="r chip"><span class="ln"></span><span class="c">{arrow} {label} '
            f'<a href="#" data-goto-file="{esc(move["path"])}">{esc(move["path"])}</a> · {move["count"]} lines</span></div>')


def gap(count, expandable=True, text=None):
    label = text or f"{count} unmodified line{'s' if count != 1 else ''}"
    icon = "<svg viewBox='0 0 16 16'><path d='M5 6l3-3 3 3M5 10l3 3 3-3'/></svg>" if expandable else \
        "<svg viewBox='0 0 16 16'><path d='M5 6.5l3 3 3-3'/></svg>" if text else \
        "<svg viewBox='0 0 16 16'><path d='M5 10l3-3 3 3'/></svg>"
    return f'<div class="gap{" x" if expandable else ""}"><span class="gi">{icon}</span><span class="gl">{label}</span></div>'


def file_body(file):
    if file["binary"]:
        return '<div class="note">Binary file</div>'
    ext, state, parts = ext_of(file["path"]), {}, []
    previous_end = None
    for number, hunk in enumerate(file["hunks"]):
        lines = hunk["lines"]
        before = hunk["new_start"] - 1 if number == 0 else hunk["new_start"] - (previous_end or hunk["new_start"])
        if file["status"] == "added":
            before = 0
        keep, marks = visible_lines(lines), inline_marks(lines)
        if before > 0 and 0 in keep:
            parts.append(gap(before, False))
        index = 0
        while index < len(lines):
            if index in keep:
                parts.append(row(lines[index], ext, state, marks.get(index)))
                if "move" in lines[index]:
                    parts.append(chip(lines[index]["move"]))
                index += 1
                continue
            end = index
            while end < len(lines) and end not in keep:
                end += 1
            hidden = "".join(row(lines[k], ext, state) + (chip(lines[k]["move"]) if "move" in lines[k] else "")
                             for k in range(index, end))
            leading = before if index == 0 and before > 0 else 0
            if end - index < 4 and not leading:
                parts.append(hidden)
            else:
                parts.append(gap(end - index + leading) + f'<div class="hid">{hidden}</div>')
            index = end
        last = [line for line in lines if "n" in line]
        previous_end = last[-1]["n"] + 1 if last else hunk["new_start"]
    if file["status"] not in ("added", "deleted") and file["hunks"]:
        parts.append(gap(0, False, "More unchanged context may be available"))
    return "".join(parts)


ICON_COLORS = {"ts": ("TS", "#3178c6"), "js": ("JS", "#c9a400"), "mjs": ("JS", "#c9a400"), "cjs": ("JS", "#c9a400"),
               "py": ("PY", "#3572a5"), "go": ("GO", "#00add8"), "rs": ("RS", "#b7410e"), "md": ("MD", "#6e7781"),
               "mdx": ("MD", "#6e7781"), "json": ("{}", "#8a8a87"), "css": ("#", "#663399"), "scss": ("#", "#c6538c"),
               "sql": ("DB", "#e38c00"), "sh": ("$", "#4e9a06"), "yml": ("Y", "#cb171e"), "yaml": ("Y", "#cb171e"),
               "toml": ("T", "#9c4221"), "html": ("<>", "#e34c26"), "rb": ("RB", "#cc342d"), "swift": ("SW", "#f05138"),
               "kt": ("KT", "#a97bff"), "java": ("JV", "#b07219"), "sol": ("SO", "#5f6b7a"), "prisma": ("PR", "#2d3748")}
REACT = ("<svg class='fi react' viewBox='-11.5 -10.2 23 20.5'><circle r='2.05'/><g fill='none' stroke-width='1'>"
         "<ellipse rx='11' ry='4.2'/><ellipse rx='11' ry='4.2' transform='rotate(60)'/>"
         "<ellipse rx='11' ry='4.2' transform='rotate(120)'/></g></svg>")


def file_icon(path):
    ext = ext_of(path)
    if ext in ("tsx", "jsx"):
        return REACT
    text, color = ICON_COLORS.get(ext, ("", "#8a8a87"))
    if not text:
        return "<svg class='fi doc' viewBox='0 0 16 16'><path d='M4 1.5h5l3 3v10H4z M9 1.5v3h3'/></svg>"
    return f"<span class='fi badge' style='--c:{color}'>{esc(text)}</span>"


def split_path(path):
    head, _, name = path.rpartition("/")
    return name, head + "/" if head else ""


def counts(additions, deletions):
    parts = []
    if additions:
        parts.append(f'<span class="plus">+{additions}</span>')
    if deletions:
        parts.append(f'<span class="minus">-{deletions}</span>')
    return " ".join(parts)


def file_card(file, prefix, collapsed_reason=None):
    name, directory = split_path(file["path"])
    status = {"added": "added", "deleted": "deleted"}.get(file["status"], "")
    if file["status"] == "renamed":
        status = f"renamed from {esc(split_path(file['old_path'])[0])}"
    total = sum(len(h["lines"]) for h in file["hunks"])
    reason = collapsed_reason
    if not reason and file["status"] == "deleted":
        reason = f"Deleted file · {file['deletions']} lines"
    if not reason and total > 800:
        reason = f"Large diff · {total} lines"
    body = file_body(file) if file["hunks"] or file["binary"] else '<div class="note">No content changes</div>'
    lazy = f'<div class="lazy"><button>{esc(reason)} · Show diff</button></div>' if reason else ""
    return f"""
<section class="file{' collapsed' if reason else ''}" id="{prefix}-{esc(file['path'])}" data-path="{esc(file['path'])}">
  <header class="fh">
    <button class="chev" aria-label="Collapse"><svg viewBox="0 0 16 16"><path d="M4.5 6.5 8 10l3.5-3.5"/></svg></button>
    {file_icon(file['path'])}<span class="fname">{esc(name)}</span><span class="fdir">{esc(directory)}</span>
    <span class="sp"></span>
    <button class="more" title="Copy path" data-copy="{esc(file['path'])}">···</button>
    <span class="fstatus">{status}</span><span class="fcount">{counts(file['additions'], file['deletions'])}</span>
    <label class="rv">Reviewed <input type="checkbox" data-review="{esc(file['path'])}"></label>
  </header>
  {lazy}<div class="fb">{body}</div>
</section>"""


INLINE_CODE = re.compile(r"`([^`]+)`")
LABEL_ICONS = {
    "database": "<svg viewBox='0 0 16 16'><ellipse cx='8' cy='3.5' rx='5' ry='2'/><path d='M3 3.5v9c0 1.1 2.2 2 5 2s5-.9 5-2v-9M3 8c0 1.1 2.2 2 5 2s5-.9 5-2'/></svg>",
    "tests": "<svg viewBox='0 0 16 16'><path d='M6 1.5h4M6.5 1.5v4.2L2.8 12.6a1.3 1.3 0 0 0 1.1 1.9h8.2a1.3 1.3 0 0 0 1.1-1.9L9.5 5.7V1.5M4.5 9.5h7'/></svg>",
    "generated": "<svg viewBox='0 0 16 16'><circle cx='8' cy='8' r='2.2'/><path d='M8 1.5v2M8 12.5v2M1.5 8h2M12.5 8h2M3.4 3.4l1.4 1.4M11.2 11.2l1.4 1.4M3.4 12.6l1.4-1.4M11.2 4.8l1.4-1.4'/></svg>",
}


def prose(text):
    parts = INLINE_CODE.split(text or "")
    return "".join(f"<code>{esc(p)}</code>" if i % 2 else esc(p) for i, p in enumerate(parts))


def tree_block(block, chapters):
    rows, plus, minus = [], 0, 0
    for line in block.get("lines", []):
        op = line.get("op", " ")
        plus += op == "+"
        minus += op == "-"
        kind = {"+": "add", "-": "del"}.get(op, "ctx")
        ref = line.get("ref")
        if isinstance(ref, int) and 1 <= ref <= len(chapters):
            ref_html = f'<a class="ref" href="#ch-{ref}">{ref:02d}</a>'
        else:
            ref_html = f'<span class="ref">{esc(str(ref))}</span>' if ref else '<span class="ref"></span>'
        note = f' <span class="tnote">{esc(line["note"])}</span>' if line.get("note") else ""
        pad = int(line.get("depth", 0)) * 2
        rows.append(f'<div class="tr {kind}"><span class="sg">{"" if op == " " else op}</span>'
                    f'<span class="tt" style="--d:{pad}ch">{esc(line["text"].replace("`", ""))}{note}</span>{ref_html}</div>')
    return "".join(rows), plus, minus


BRANCH_ICON = ("<span class='dicon'><svg viewBox='0 0 16 16'><circle cx='4' cy='8' r='1.5'/><circle cx='12' cy='4' r='1.5'/>"
               "<circle cx='12' cy='12' r='1.5'/><path d='M5.5 8h2.5M8 8V5.5a1.5 1.5 0 0 1 1.5-1.5h1M8 8v2.5a1.5 1.5 0 0 0 1.5 1.5h1'/></svg></span>")


def diagram_block(block, chapters):
    """Capy-style flow: nodes on a grid of lanes; guide.js draws the rounded orthogonal wires between them."""
    nodes = {node["id"]: node for node in block["nodes"]}
    columns = max(len(row) for row in block["rows"])
    cells = []
    for row in block["rows"]:
        for column in range(columns):
            node_id = row[column] if column < len(row) else None
            if not node_id:
                cells.append('<div class="dcell"></div>')
                continue
            node = nodes[node_id]
            kind = node.get("type", "plain")
            tag = node.get("tag", "")
            dot = "<i></i>" if kind in ("new", "decision", "removed") else ""
            sign = {"new": "+", "removed": "−"}.get(kind, "") if not tag else ""
            ref = f'<a class="dref" href="#ch-{node["ref"]}">{node["ref"]:02d}</a>' if isinstance(node.get("ref"), int) else ""
            cells.append(
                f'<div class="dcell"><div class="dnode {esc(kind)}{"" if tag else " flat"}" data-id="{esc(node_id)}">'
                f'{BRANCH_ICON if kind == "decision" else ""}<div class="dbody">'
                f'{f"<div class=dtag>{dot}{esc(tag)}</div>" if tag else ""}'
                f'<div class="dtext">{f"<b>{sign}</b>" if sign else ""}{esc(node.get("text", "").replace("`", ""))}</div></div>{ref}</div></div>')
    edges = esc(json.dumps(block.get("edges", [])))
    return (f'<div class="diagram" data-edges="{edges}"><svg class="dwires"></svg>'
            f'<div class="dgrid" style="--cols:{columns}">{"".join(cells)}</div></div>')


def validate_diagram(block):
    errors, nodes = [], {node.get("id") for node in block.get("nodes", [])}
    placed = [node_id for row in block.get("rows", []) for node_id in row if node_id]
    if not 2 <= len(nodes) <= 8:
        errors.append("a diagram needs 2–8 nodes; use a tree instead")
    if not block.get("rows") or len(block["rows"]) > 4 or max(len(row) for row in block["rows"]) > 4:
        errors.append("a diagram needs 1–4 rows of at most 4 nodes; use a tree instead")
    if sorted(placed) != sorted(nodes):
        errors.append("every diagram node must appear exactly once in rows")
    for node in block.get("nodes", []):
        if len(node.get("text", "")) > 44:
            errors.append(f"diagram node '{node.get('id')}' text is over 44 characters")
    for edge in block.get("edges", []):
        if edge.get("from") not in nodes or edge.get("to") not in nodes:
            errors.append(f"diagram edge {edge.get('from')} → {edge.get('to')} names a missing node")
    return errors


def before_after(blocks, chapters):
    cards = []
    for block in blocks:
        if block.get("kind") == "diagram":
            body, plus, minus = diagram_block(block, chapters), 0, 0
            plus = sum(n.get("type") == "new" for n in block.get("nodes", []))
            minus = sum(n.get("type") == "removed" for n in block.get("nodes", []))
            body = f'<div class="bac">{esc(block.get("caption", ""))}</div>{body}'
        else:
            rows, plus, minus = tree_block(block, chapters)
            body = f'<div class="bac">{esc(block.get("caption", ""))}</div><div class="tree">{rows}</div>'
        tag = f'<span class="bal">{esc(block["label"])}</span>' if block.get("label") else ""
        cards.append(f"""
<section class="file ba">
  <header class="fh"><button class="chev" aria-label="Collapse"><svg viewBox="0 0 16 16"><path d="M4.5 6.5 8 10l3.5-3.5"/></svg></button>
    <span class="fname">Before / after</span>{tag}<span class="sp"></span><span class="fcount">{counts(plus, minus)}</span></header>
  <div class="fb">{body}</div>
</section>""")
    return "".join(cards)


def rail(chapters, active):
    ticks = ['<a class="tick{}" href="#overview" data-title="Overview"></a>'.format(" on" if active == 0 else "")]
    for number, chapter in enumerate(chapters, 1):
        labelled = chapter.get("label") in LABELS
        first_labelled = labelled and (number == 1 or chapters[number - 2].get("label") not in LABELS)
        ticks.append(f'<a class="tick{" on" if number == active else ""}{" brk" if first_labelled else ""}" '
                     f'href="#ch-{number}" data-title="{number:02d}  {esc(chapter["title"])}"></a>')
    return f'<nav class="rail">{"".join(ticks)}</nav>'


def paragraphs(text):
    return "".join(f'<p class="desc">{prose(part.strip())}</p>' for part in re.split(r"\n\s*\n", text) if part.strip())


def file_row(file):
    name, directory = split_path(file["path"])
    return (f'<a class="frow" href="#g-{esc(file["path"])}" data-path="{esc(file["path"])}">{file_icon(file["path"])}'
            f'<span class="fname">{esc(name)}</span><span class="fdir">{esc(directory)}</span>'
            f'<span class="fcount">{counts(file["additions"], file["deletions"])}</span></a>')


def validate(data, guide):
    errors = []
    paths = [f["path"] for f in data["files"]]
    tests = {f["path"] for f in data["files"] if f["label"] == "tests"}
    seen = {}
    if not guide.get("overview", {}).get("summary"):
        errors.append("overview.summary is required")
    chapters = guide.get("chapters") or []
    if not chapters:
        errors.append("at least one chapter is required")
    for number, chapter in enumerate(chapters, 1):
        for key in ("title", "summary", "files"):
            if not chapter.get(key):
                errors.append(f"chapter {number}: '{key}' is required")
        if chapter.get("label") not in (None, *LABELS):
            errors.append(f"chapter {number}: label must be one of {', '.join(LABELS)}")
        for path in chapter.get("files", []):
            if path not in paths:
                errors.append(f"chapter {number}: '{path}' is not in the diff")
            elif path in tests:
                errors.append(f"chapter {number}: '{path}' is a test file; leave it out (it stays in the Diff tab)")
            elif path in seen:
                errors.append(f"'{path}' appears in chapters {seen[path]} and {number}")
            seen.setdefault(path, number)
    labelled = [c.get("label") in LABELS for c in chapters]
    if any(labelled[i] and not labelled[i + 1] for i in range(len(labelled) - 1)):
        errors.append("labelled chapters (database, generated) must come after all other chapters")
    for path in paths:
        if path not in seen and path not in tests:
            errors.append(f"'{path}' is not in any chapter")
    blocks = guide.get("overview", {}).get("before_after") or []
    for block in blocks if isinstance(blocks, list) else [blocks]:
        for item in block.get("lines", []) + block.get("nodes", []):
            ref = item.get("ref")
            if isinstance(ref, int) and not 1 <= ref <= len(chapters):
                errors.append(f"before/after ref {ref} does not match a chapter")
        if block.get("kind") == "diagram":
            errors.extend(validate_diagram(block))
    return errors


def render(args):
    directory = Path(args.dir)
    data = json.loads((directory / "diff.json").read_text())
    guide = json.loads((directory / "guide.json").read_text())
    errors = validate(data, guide)
    if errors:
        print("guide.json needs fixes:\n  - " + "\n  - ".join(errors), file=sys.stderr)
        raise SystemExit(1)
    meta, files = data["meta"], {f["path"]: f for f in data["files"]}
    chapters, overview = guide["chapters"], guide["overview"]
    blocks = overview.get("before_after") or []
    blocks = blocks if isinstance(blocks, list) else [blocks]
    title = guide.get("title") or meta["title"]
    additions = sum(f["additions"] for f in files.values())
    deletions = sum(f["deletions"] for f in files.values())
    total = len(chapters)

    steps = "".join(f"<li>{prose(s)}</li>" for s in overview.get("steps", []))
    test_count = sum(f["label"] == "tests" for f in files.values())
    tests_note = (f'<p class="tnote-files">{test_count} test file{"s" if test_count != 1 else ""} '
                  f'<a href="#" data-tab-link="diff">in the Diff tab</a></p>') if test_count else ""
    sections = [f"""
<div class="chapter" id="overview">
  <div class="left">{rail(chapters, 0)}
    <h2>Overview</h2>
    <p class="desc">{prose(overview['summary'])}</p>{f'<ol class="steps">{steps}</ol>' if steps else ''}{tests_note}
  </div>
  <div class="right">{before_after(blocks, chapters)}</div>
</div>"""]
    for number, chapter in enumerate(chapters, 1):
        label = chapter.get("label")
        tag = f'<span class="clabel">{LABEL_ICONS[label]}{label.title()}</span>' if label else ""
        chapter_files = [files[p] for p in chapter["files"]]
        cards = "".join(file_card(f, "g", "Generated" if label == "generated" else None) for f in chapter_files)
        rows = "".join(file_row(f) for f in chapter_files)
        sections.append(f"""
<div class="chapter" id="ch-{number}" data-files="{esc(json.dumps(chapter['files']))}">
  <div class="left">{rail(chapters, number)}
    <h2>{esc(chapter['title'])}</h2>
    <div class="cmeta"><span class="cnum">{number:02d} / {total:02d}</span>{tag}
      <label class="rv">Reviewed <input type="checkbox" data-chapter="{number}"></label></div>
    {paragraphs(chapter['summary'])}
    <div class="flist">{rows}</div>
  </div>
  <div class="right">{cards}</div>
</div>""")

    ordered = sorted(files.values(), key=lambda f: f["path"])
    labels = {path: chapter.get("label") for chapter in chapters for path in chapter["files"]}
    diff_tab = (f'<div class="files"><div class="files-head">Files <span>{len(ordered)}</span></div>'
                f'<div class="files-grid">{"".join(file_row(f) for f in ordered)}</div></div>'
                + "".join(file_card(f, "d", "Generated" if labels.get(f["path"]) == "generated" else None) for f in ordered))
    body = prose(meta.get("body") or "") or '<span class="muted">No description.</span>'
    avatar = (f'<img class="av" src="https://github.com/{esc(meta["login"])}.png?size=40" alt="">'
              if meta.get("login") else f'<span class="av">{esc((meta.get("author") or "?")[:1].upper())}</span>')
    number = f'<span class="sep"></span><span>#{meta["number"]}</span>' if meta.get("number") else ""
    open_pr = (f'<a class="btn primary" href="{esc(meta["url"])}" target="_blank" rel="noopener">'
               f'<svg viewBox="0 0 16 16"><circle cx="4" cy="3.5" r="1.6"/><circle cx="4" cy="12.5" r="1.6"/>'
               f'<circle cx="12" cy="12.5" r="1.6"/><path d="M4 5.1v5.8M12 10.9V7a2.5 2.5 0 0 0-2.5-2.5H7M8.5 3 7 4.5 8.5 6"/></svg>'
               f'Open PR</a>') if meta.get("url") else ""

    page = (ASSETS / "template.html").read_text()
    replacements = {
        "{{TITLE}}": esc(title), "{{CSS}}": (ASSETS / "guide.css").read_text(), "{{JS}}": (ASSETS / "guide.js").read_text(),
        "{{COUNTS}}": counts(additions, deletions), "{{AVATAR}}": avatar, "{{AUTHOR}}": esc(meta.get("author") or ""),
        "{{NUMBER}}": number, "{{HEAD}}": esc(short(meta.get("head"))), "{{CREATED}}": esc(meta.get("created_at") or ""), "{{OPEN_PR}}": open_pr,
        "{{GUIDE}}": "".join(sections), "{{DIFF}}": diff_tab, "{{BODY}}": body,
        "{{BRANCH}}": esc(f"{meta.get('base_ref')} ← {meta.get('head_ref')}"), "{{FILES}}": str(len(files)),
        "{{KEY}}": esc(f"review-guide:{meta.get('repo')}:{meta.get('number') or meta.get('head_ref')}:{meta.get('head')}"),
    }
    page = re.sub(r"\{\{[A-Z_]+\}\}", lambda match: replacements.get(match[0], match[0]), page)
    out = directory / "review-guide.html"
    out.write_text(page)
    tests = sum(f["label"] == "tests" for f in files.values())
    print(f"Validated: {len(files) - tests} files in {len(chapters)} chapters, each in exactly one; "
          f"{tests} test files left to the Diff tab.")
    if (directory / "diff.patch").exists():
        (directory / "rendered.patch").write_text((directory / "diff.patch").read_text())
    (directory / "rendered.json").write_text(json.dumps(
        {"head": meta.get("head"), "files": {path: fingerprint(file) for path, file in files.items()}}))
    print(out)


def pending(args):
    """List open PRs whose guide is missing or was rendered for an older head."""
    prs = json.loads(run("gh", "pr", "list", "--state", "open", "--author", args.author, "--limit", "100",
                         "--json", "number,title,headRefOid"))
    guides = Path(git("rev-parse", "--path-format=absolute", "--git-common-dir").strip()) / "review-guides"
    stale = []
    for pr in prs:
        snapshot = guides / str(pr["number"]) / "rendered.json"
        head = json.loads(snapshot.read_text()).get("head") if snapshot.exists() else None
        if head != pr["headRefOid"]:
            state = f"push {short(head)} → {short(pr['headRefOid'])}" if head else "no guide yet"
            stale.append(f"  #{pr['number']:<6} {state:<26} {pr['title']}")
    print("\n".join(["Guides to write or update:"] + stale) if stale else "Every open PR has a current guide.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    collect_parser = commands.add_parser("collect", help="Gather the diff for a PR, branch or working tree")
    collect_parser.add_argument("--pr", help="GitHub PR number or URL (uses gh)")
    collect_parser.add_argument("--base", help="Base ref (default: merge-base with origin's default branch)")
    collect_parser.add_argument("--head", help="Head ref (default: working tree, including uncommitted changes)")
    collect_parser.add_argument("--out", help="Output directory (default: <git-dir>/review-guides/<pr-or-branch>)")
    render_parser = commands.add_parser("render", help="Render diff.json + guide.json into review-guide.html")
    render_parser.add_argument("dir")
    pending_parser = commands.add_parser("pending", help="List open PRs whose guide is missing or out of date")
    pending_parser.add_argument("--author", default="@me", help="PR author filter for gh (default: @me)")
    args = parser.parse_args()
    {"collect": collect, "render": render, "pending": pending}[args.command](args)


if __name__ == "__main__":
    main()

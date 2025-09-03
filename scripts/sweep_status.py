# chore(docs): add docs status sweep CLI
#
# Deterministic checker/updater for docs statuses across the backlog.
# stdlib only; runs offline. See --help for usage.

from __future__ import annotations

import argparse
import dataclasses as dc
import difflib
import re
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


@dc.dataclass
class LeafStatus:
    path: Path
    title: str
    status: str  # DONE|PARTIAL|TODO
    header_status: str | None = None
    checked: int = 0
    total: int = 0


STATUS_RE = re.compile(r"^#\s+(DONE|TODO)\s+—\s+(.*)$")
STATUS_LINE_RE = re.compile(r"^Status:\s*(Complete|Partial|Planned)", re.I)
CHECKBOX_RE = re.compile(r"^\s*- \[([ xX])\]\s+(.*)$")


def discover_md(include: list[str] | None = None, exclude: list[str] | None = None) -> list[Path]:
    include = include or ["**/*.md"]
    exclude = set(exclude or [
        "guides/archive/**",
        "adr/**",
    ])
    out: list[Path] = []
    for pat in include:
        for p in DOCS.glob(pat):
            rel = p.relative_to(DOCS)
            skip = any(rel.match(ex) for ex in exclude)
            # allow ADR/TODO exceptions
            if skip and "TODO" not in p.name:
                continue
            out.append(p)
    return sorted(set(out))


def infer_leaf_status(path: Path) -> LeafStatus:
    text = path.read_text(encoding="utf-8").splitlines()
    header_status = None
    title = path.stem
    checked = total = 0
    status_line_hint: str | None = None

    for i, line in enumerate(text[:50]):  # examine top of file
        m = STATUS_RE.match(line.strip())
        if m:
            header_status = m.group(1).upper()
            title = m.group(2).strip()
            break

    for line in text:
        m = CHECKBOX_RE.match(line)
        if m:
            total += 1
            if m.group(1).lower() == "x":
                checked += 1
        m2 = STATUS_LINE_RE.match(line)
        if m2 and not status_line_hint:
            hint = m2.group(1).lower()
            status_line_hint = {"complete": "DONE", "partial": "PARTIAL", "planned": "TODO"}.get(hint)

    # conservative inference
    if header_status == "DONE":
        status = "DONE"
    elif checked > 0 and checked < total:
        status = "PARTIAL"
    else:
        status = "TODO"

    return LeafStatus(path=path, title=title, status=status, header_status=header_status, checked=checked, total=total)


def map_rewrite_leaves() -> dict[str, LeafStatus]:
    leaves: dict[str, LeafStatus] = {}
    for p in (DOCS / "backlog/rewrite").glob("TODO-*.md"):
        leaves[p.name] = infer_leaf_status(p)
    return leaves


@dc.dataclass
class PlannedEdit:
    path: Path
    before: str
    after: str


def replace_lines(text: str, replacements: dict[int, str]) -> str:
    out_lines = []
    for i, line in enumerate(text.splitlines()):
        if i in replacements:
            out_lines.append(replacements[i])
        else:
            out_lines.append(line)
    return "\n".join(out_lines) + ("\n" if text.endswith("\n") else "")


def reconcile_rewrite_index(leaves: dict[str, LeafStatus]) -> PlannedEdit | None:
    path = DOCS / "backlog/rewrite/README.md"
    text = path.read_text(encoding="utf-8")
    repl: dict[int, str] = {}
    in_section = False
    pat = re.compile(r"^-\s+(DONE|PARTIAL|TODO)\s+—\s+(.+?):\s+`\./(TODO-.*?\.md)`")
    for i, line in enumerate(text.splitlines()):
        if "Feature/Work Items (alphabetical)" in line:
            in_section = True
            continue
        if in_section:
            m = pat.match(line.strip())
            if m:
                file = m.group(3)
                if file in leaves:
                    new_status = leaves[file].status
                    if new_status != m.group(1):
                        newline = re.sub(r"^(?:DONE|PARTIAL|TODO)", new_status, line, count=1)
                        repl[i] = newline
            # stop on blank line followed by non-list content (simple heuristic)
            if line.strip() == "" and i > 0:
                # continue; section spans entire list, safe to keep scanning
                pass
    if not repl:
        return None
    after = replace_lines(text, repl)
    return PlannedEdit(path=path, before=text, after=after)


def reconcile_rewrite_todo_md(leaves: dict[str, LeafStatus]) -> PlannedEdit | None:
    path = DOCS / "backlog/rewrite/TODO.md"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    repl: dict[int, str] = {}
    pat = re.compile(r"^- \[( |x)\]\s+(.+?)\s+—\s+see\s+`(TODO-.*?\.md)`", re.I)
    for i, line in enumerate(text.splitlines()):
        m = pat.match(line.strip())
        if not m:
            continue
        file = m.group(3)
        if file in leaves:
            desired = "x" if leaves[file].status == "DONE" else " "
            if m.group(1) != desired:
                newline = re.sub(r"^- \[( |x)\]", f"- [{desired}]", line, count=1)
                repl[i] = newline
    if not repl:
        return None
    after = replace_lines(text, repl)
    return PlannedEdit(path=path, before=text, after=after)


def reconcile_todos_index() -> PlannedEdit | None:
    path = DOCS / "backlog/todos/README.md"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    leaf = DOCS / "backlog/todos/0004-sandbox-fs-todo.md"
    if not leaf.exists():
        return None
    leaf_status = infer_leaf_status(leaf)
    # Infer conservatively for track: only DONE with explicit H1 DONE
    if leaf_status.header_status == "DONE":
        status = "DONE"
    elif leaf_status.checked > 0 and leaf_status.total > 0 and leaf_status.checked < leaf_status.total:
        status = "PARTIAL"
    else:
        status = "TODO"
    repl: dict[int, str] = {}
    pat = re.compile(r"^-\s+(DONE|PARTIAL|TODO)\s+—\s+Filesystem Sandbox & Safety Work Items.*`\./0004-sandbox-fs-todo\.md`")
    for i, line in enumerate(text.splitlines()):
        m = pat.match(line.strip())
        if m and m.group(1) != status:
            newline = re.sub(r"^(?:-\s+)(DONE|PARTIAL|TODO)", f"- {status}", line, count=1)
            repl[i] = newline
    if not repl:
        return None
    after = replace_lines(text, repl)
    return PlannedEdit(path=path, before=text, after=after)


def reconcile_docs_readme() -> PlannedEdit | None:
    path = DOCS / "README.md"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    repl: dict[int, str] = {}
    pat = re.compile(r"^-\s+(DONE|PARTIAL|TODO)\s+—\s+(.+?):\s+`\./backlog/.*?\.md`", re.I)
    for i, line in enumerate(text.splitlines()):
        m = pat.match(line.strip())
        if not m:
            continue
        # Try to map to an absolute file within docs; if missing, skip
        rel_match = re.search(r"`\.(/backlog/.*?\.md)`", line)
        if not rel_match:
            continue
        doc_rel = rel_match.group(1)
        fpath = DOCS / doc_rel.lstrip("/")
        if not fpath.exists():
            continue
        leaf = infer_leaf_status(fpath)
        status = leaf.status
        # conservative: never auto-promote to DONE unless H1 says DONE
        top = (fpath.read_text(encoding="utf-8").splitlines() or [""])[0].strip()
        m = STATUS_RE.match(top)
        desired = "DONE" if (m and m.group(1) == "DONE") else status
        if desired != m.group(1):
            repl[i] = re.sub(r"^(?:-\s+)(DONE|PARTIAL|TODO)", f"- {desired}", line, count=1)
    if not repl:
        return None
    after = replace_lines(text, repl)
    return PlannedEdit(path=path, before=text, after=after)


def reconcile_status_md(leaves: dict[str, LeafStatus]) -> PlannedEdit | None:
    path = ROOT / "STATUS.md"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    repl: dict[int, str] = {}
    # Target a narrow, safe update: ensure Examples Parity mention includes DONE when leaf is DONE
    examples = leaves.get("TODO-examples-parity.md")
    if examples and examples.status == "DONE":
        for i, line in enumerate(text.splitlines()):
            if "Examples Parity" in line and re.match(r"^\s*-\s*\[?x?\]?|\s*-\s*DONE|\s*-\s*TODO", line, flags=re.I):
                # Keep line but ensure DONE token appears prominently
                if "DONE" not in line:
                    repl[i] = re.sub(r"^(\s*-\s*)(?:TODO|PARTIAL)?", r"\\1DONE: ", line)
    if not repl:
        return None
    after = replace_lines(text, repl)
    return PlannedEdit(path=path, before=text, after=after)


def compute_edits(write: bool, verbose: bool) -> list[PlannedEdit]:
    leaves = map_rewrite_leaves()
    edits: list[PlannedEdit] = []
    for fn in (
        reconcile_rewrite_index(leaves),
        reconcile_rewrite_todo_md(leaves),
        reconcile_todos_index(),
        reconcile_docs_readme(),
        reconcile_status_md(leaves),
    ):
        if fn:
            edits.append(fn)
    return edits


def show_or_apply(edits: Iterable[PlannedEdit], write: bool) -> int:
    changes = 0
    for e in edits:
        if e.before == e.after:
            continue
        changes += 1
        if write:
            e.path.write_text(e.after, encoding="utf-8")
        else:
            diff = difflib.unified_diff(
                e.before.splitlines(), e.after.splitlines(),
                fromfile=str(e.path) + " (current)", tofile=str(e.path) + " (expected)", lineterm="",
            )
            print("\n".join(diff))
    return changes


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Docs status sweep: verify or update status consistency across docs.")
    ap.add_argument("--write", action="store_true", help="Apply fixes in place (default: check only)")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)

    edits = compute_edits(write=args.write, verbose=args.verbose)
    changed = show_or_apply(edits, write=args.write)
    if changed == 0:
        print("No changes required.")
        return 0
    return 0 if args.write else 1


if __name__ == "__main__":
    raise SystemExit(main())

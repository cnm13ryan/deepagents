#!/usr/bin/env python3
"""
Conventional Commit path guard for selected types.

Enforces that commits of type `test`, `docs`, and `chore` only touch
allowed paths unless explicitly bypassed.

Usage modes:
  1) Pre-commit commit-msg hook:
     scripts/commit_guard.py --commit-msg-file <path>
     - Reads commit subject from <path>
     - Reads staged files via `git diff --name-only --cached`

  2) CI commit range mode:
     scripts/commit_guard.py --range <BASE>..<HEAD>
     - Iterates commits in the range and validates each one.

Bypass options:
  - Include "[skip-commit-guard]" anywhere in the commit message, or
    add a trailer line "Allow-Guard-Bypass: true" to skip enforcement.

Exit codes:
  0 = OK (or bypassed / non-target types)
  1 = Violations detected
  2 = Usage error
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

CONVENTIONAL_RE = re.compile(r"^(?P<type>\w+)(?:\([^)]*\))?:\s*")
BYPASS_PATTERNS = (
    "[skip-commit-guard]",
    "Allow-Guard-Bypass: true",
)


def run(cmd: Sequence[str], *, cwd: str | None = None) -> str:
    res = subprocess.run(cmd, cwd=cwd, check=False, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Command failed ({res.returncode}): {' '.join(cmd)}\n{res.stderr}")
    return res.stdout


def staged_files() -> list[str]:
    out = run(["git", "diff", "--name-only", "--cached"]).strip()
    return [p for p in out.splitlines() if p]


def commit_files(commit: str) -> list[str]:
    out = run(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit]).strip()
    return [p for p in out.splitlines() if p]


def commit_subject(commit: str) -> str:
    out = run(["git", "log", "-n", "1", "--pretty=%s", commit]).rstrip("\n")
    return out


def parse_type(subject: str) -> str | None:
    m = CONVENTIONAL_RE.match(subject)
    return m.group("type") if m else None


def has_bypass(message: str) -> bool:
    lower = message.lower()
    return any(tag.lower() in lower for tag in BYPASS_PATTERNS)


def is_merge_or_revert(subject: str) -> bool:
    s = subject.lower()
    return s.startswith("merge ") or s.startswith("revert ")


@dataclass
class Rule:
    type_name: str
    allowed: tuple[str, ...]

    def violations(self, paths: Iterable[str]) -> list[str]:
        bad: list[str] = []
        for p in paths:
            if any(fnmatch.fnmatch(p, pat) for pat in self.allowed):
                continue
            bad.append(p)
        return bad


# Allowed path patterns for each type. Patterns are matched via fnmatch.
RULES: dict[str, Rule] = {
    "test": Rule(
        "test",
        allowed=(
            "tests/**",
            # Allow top-level testing docs
            "docs/TESTING*.md",
            "README.md",
        ),
    ),
    "docs": Rule(
        "docs",
        allowed=(
            "docs/**",
            "mkdocs.yml",
            "README*.md",
            "AGENTS.md",
            "CONTRIBUTING.md",
            "STATUS.md",
            # Example READMEs and markdown docs within examples are considered docs
            "examples/**/README*.md",
            "examples/**/*.md",
            "overrides/**",
            "*.png",
            "*.svg",
        ),
    ),
    "chore": Rule(
        "chore",
        allowed=(
            # CI & repo config
            ".github/**",
            ".gitignore",
            ".gitattributes",
            ".gitmodules",
            ".pre-commit-config.yaml",
            # Scripts & tooling
            "scripts/**",
            "configure.py",
            # Packaging / deps / env
            "pyproject.toml",
            "uv.lock",
            "env_templates/**",
            # Meta docs allowed for housekeeping
            "README*.md",
            "AGENTS.md",
            "CONTRIBUTING.md",
            "STATUS.md",
        ),
    ),
}


def check_one(subject: str, files: Sequence[str]) -> tuple[bool, str]:
    """Return (ok, message)."""
    if has_bypass(subject) or is_merge_or_revert(subject):
        return True, "bypass/merge/revert"

    cc_type = parse_type(subject)
    if not cc_type or cc_type not in RULES:
        return True, "non-target type"

    rule = RULES[cc_type]
    bad = rule.violations(files)
    if not bad:
        return True, "ok"

    lines = [
        f"Commit type '{cc_type}' is restricted to: {', '.join(rule.allowed)}",
        "Found out-of-scope paths:",
        *[f"  - {p}" for p in bad],
        "\nOptions:",
        "  - Split the commit so non-test/docs/chore changes use an appropriate type (e.g., feat/refactor).",
        "  - If intentional, add '[skip-commit-guard]' to the commit message to bypass.",
    ]
    return False, "\n".join(lines)


def mode_commit_msg_file(msg_file: str) -> int:
    with open(msg_file, encoding="utf-8") as f:
        message = f.read()
    subject = message.splitlines()[0] if message else ""
    files = staged_files()
    ok, details = check_one(subject, files)
    if ok:
        return 0
    sys.stderr.write(f"Commit-Guard: {subject}\n{details}\n")
    return 1


def mode_range(range_expr: str) -> int:
    # Expand to a list of SHAs newest-first
    revs = run(["git", "rev-list", range_expr]).splitlines()
    rc = 0
    for sha in reversed(revs):  # oldest -> newest for readable output
        subject = commit_subject(sha)
        files = commit_files(sha)
        ok, details = check_one(subject, files)
        if not ok:
            rc = 1
            sys.stderr.write(f"Commit-Guard: {sha[:12]} {subject}\n{details}\n\n")
    return rc


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Conventional Commit path guard")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--commit-msg-file", dest="msg_file", help="Path to commit message file (pre-commit)")
    g.add_argument("--range", dest="range_expr", help="Commit range expression, e.g., BASE..HEAD (CI)")
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(argv or sys.argv[1:])
    try:
        ns = parse_args(argv)
        if ns.msg_file:
            return mode_commit_msg_file(ns.msg_file)
        return mode_range(ns.range_expr)
    except RuntimeError as e:
        sys.stderr.write(str(e) + "\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())

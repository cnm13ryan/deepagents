---
title: "edit_file Reference"
status: draft
kind: builtin
mode: stateless
owner: docs
---

# edit_file

## Overview
- Performs a single-string replace (first or all occurrences) then writes back.
- Use for precise, atomic edits.
- Classification: stateless.

## Parameters
- path: string — Target file. Required.
- find: string — Text to replace. Required.
- replace: string — Replacement text. Required.
- all: bool — Replace all occurrences. Default: false.

## Result Schema
- replacements: int — Count of replacements applied.
- diff_preview: string — Optional short diff.
- errors: list[str]

## Timeouts & Limits
- Execution timeout: TBD. Max file size: TBD.

## Examples
```
Replace a config key across a file.
```

## Safety & Best Practices
- Prefer exact matches; test on a small sample before global replace.

## Troubleshooting
- No matches — Verify `find` string and file encoding.

## Source of Truth
- Code: src/inspect_agents/tools_files.py


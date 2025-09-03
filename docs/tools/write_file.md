---
title: "write_file Reference"
status: draft
kind: builtin
mode: stateless
owner: docs
---

# write_file

## Overview
- Writes content to a file with bounded timeout; creates or overwrites.
- Classification: stateless.

## Parameters
- path: string — Destination path. Required.
- content: string — File body. Required.

## Result Schema
- bytes_written: int
- created: bool
- errors: list[str]

## Timeouts & Limits
- Execution timeout: TBD. Max size: TBD. Newline normalization: TBD.

## Examples
```
Write a small markdown note to docs/note.md.
```

## Safety & Best Practices
- Avoid large binary blobs; prefer small, textual diffs.

## Troubleshooting
- Permission denied — Check sandbox mode and path.

## Source of Truth
- Code: src/inspect_agents/tools_files.py


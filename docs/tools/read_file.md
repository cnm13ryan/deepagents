---
title: "read_file Reference"
status: draft
kind: builtin
mode: stateless
owner: docs
---

# read_file

## Overview
- Returns numbered lines from a file with truncation and bounds checks.
- Use to inspect code/docs with optional line ranges.
- Classification: stateless.

## Parameters
- path: string — File path. Required.
- start/end: int — Optional 1-indexed line bounds.

## Result Schema
- content: string — Returned text (may be truncated).
- range: { start: int, end: int } — Lines returned.
- truncated: bool — True if longer than cap.

## Timeouts & Limits
- Execution timeout: TBD. Line/byte caps: TBD. Truncation policy: TBD.

## Examples
```
Read lines 1-200 of docs/README.md.
```

## Safety & Best Practices
- Prefer specific ranges to keep outputs small.

## Troubleshooting
- File not found — Verify path and sandbox root.

## Source of Truth
- Code: src/inspect_agents/tools_files.py
- Guides: ../guides/tool-umbrellas.md


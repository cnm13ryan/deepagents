---
title: "ls Reference"
status: draft
kind: builtin
mode: stateless
owner: docs
---

# ls

## Overview
- Lists filenames in the in-memory Files store (or sandbox FS via proxy).
- Use to discover files before read/edit operations.
- Classification: stateless.

## Parameters
- path/glob: string — Directory or pattern. Required.
- instance: string — Optional namespace.

## Result Schema
- files: list[string] — Matched paths.
- truncated: bool — True if results were truncated.

## Timeouts & Limits
- Execution timeout: TBD. Result count cap: TBD.

## Examples
```
List project sources under src/.
```

## Safety & Best Practices
- In sandbox mode, paths are confined to the mounted root.

## Troubleshooting
- No results — Check path relative to workspace root or namespace.

## Source of Truth
- Code: src/inspect_agents/tools_files.py
- Guides: ../guides/tool-umbrellas.md


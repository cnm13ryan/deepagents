---
title: "edit_file Reference"
status: draft
kind: builtin
mode: stateless
owner: docs
---

# edit_file

## Overview
- Performs a single‑string replace (first occurrence by default; or all with a flag) and writes the result back.
- Use for targeted, atomic edits.
- Classification: stateless.

## Parameters
- file_path: string — Target file. Required.
- old_string: string — Text to replace. Required.
- new_string: string — Replacement text. Required.
- replace_all: bool — Replace all occurrences when true (default: false).
- instance: string — Optional `Files` instance name for isolation.

## Result Schema
- Default: string — Summary message (e.g., “Updated file <path>”).
- Typed (when `INSPECT_AGENTS_TYPED_RESULTS=1`): `{ path: string, replaced: int, summary: string }` (`FileEditResult`).
  - Note: In sandbox mode the reported `replaced` count may be approximate.

## Timeouts & Limits
- Execution timeout: 15s; no explicit size cap; string replace semantics.

## Sandbox Notes
- When `INSPECT_AGENTS_FS_MODE=sandbox` and sandbox is available, routes to `text_editor('str_replace', path, old_str, new_str)`. If the sandbox is unavailable, it falls back to the in‑memory store.
- Delete operations are disabled in sandbox mode (applies across file tools); `delete_file` is store‑only.

## Examples
### Typed vs Legacy (quick look)

Args
```json
{"file_path": "app.py", "old_string": "foo", "new_string": "bar"}
```

Typed
```json
{ "path": "app.py", "replaced": 1, "summary": "Updated file app.py" }
```

Legacy
```
Updated file app.py
```

See also: [Typed Results vs Legacy Outputs](typed_results.md).

## Safety & Best Practices
- Prefer precise `old_string` values; test a single replacement before enabling `replace_all`.

## Troubleshooting
- String not found — Verify the exact `old_string` (including whitespace and casing).

## Source of Truth
- Code: src/inspect_agents/tools_files.py (execute_edit), src/inspect_agents/tools.py (edit_file wrapper)
- See also: [files](files.md) (unified files tool)

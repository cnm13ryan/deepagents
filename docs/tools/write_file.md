---
title: "write_file Reference"
status: draft
kind: builtin
mode: stateless
owner: docs
---

# write_file

## Overview
- Creates or overwrites a file’s contents with a bounded timeout.
- Classification: stateless.

## Parameters
- file_path: string — Destination path. Required.
- content: string — File body. Required.
- instance: string — Optional `Files` instance name for isolation.

## Result Schema
- Default: string — Summary message (e.g., “Updated file <path>”).
- Typed (when `INSPECT_AGENTS_TYPED_RESULTS=1`): `{ path: string, summary: string }` (`FileWriteResult`).

## Timeouts & Limits
- Execution timeout: 15s; no explicit size cap in store mode; sandbox editor may impose its own; no newline normalization.

## Sandbox Notes
- When `INSPECT_AGENTS_FS_MODE=sandbox` and sandbox is available, routes to `text_editor('create', path, file_text=...)`. On sandbox failure, falls back to the in‑memory store.
- Delete operations are disabled in sandbox mode (separate `delete_file` tool is store‑only).

## Examples
### Typed vs Legacy (quick look)

Args
```json
{"file_path": "docs/note.md", "content": "Hello"}
```

Typed
```json
{ "path": "docs/note.md", "summary": "Updated file docs/note.md" }
```

Legacy
```
Updated file docs/note.md
```

See also: [Typed Results vs Legacy Outputs](typed_results.md).

## Safety & Best Practices
- Avoid large binary blobs; prefer small, textual diffs.

## Troubleshooting
- Permission denied or sandbox errors — Ensure sandbox is available or switch to store mode; verify the path is within the sandbox root.

## Source of Truth
- Code: src/inspect_agents/tools_files.py (execute_write), src/inspect_agents/tools.py (write_file wrapper)
- See also: [files](files.md) (unified files tool)

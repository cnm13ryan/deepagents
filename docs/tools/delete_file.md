---
title: "delete_file Reference"
status: draft
kind: builtin
mode: stateless
owner: docs
---

# delete_file

## Overview
- Deletes a file from the in‑memory `Files` store. Not supported in sandbox mode for safety.
- Classification: stateless.

## Parameters
- file_path: string — Path to delete. Required.
- instance: string — Optional `Files` instance name for isolation.

## Result Schema
- Default: string — Summary message (deleted or idempotent no‑op).
- Typed (when `INSPECT_AGENTS_TYPED_RESULTS=1`): `{ path: string, summary: string }` (`FileDeleteResult`).

## Timeouts & Limits
- Execution timeout: 15s (configurable via `INSPECT_AGENTS_TOOL_TIMEOUT`).

## Sandbox Notes
- Sandbox mode: not supported — attempting to delete raises a `ToolException("delete unsupported in sandbox mode")`.
- Use the unified [files](files.md) tool or wrappers like [read_file](read_file.md), [write_file](write_file.md), [edit_file](edit_file.md) for other operations.

## Examples
### Typed vs Legacy (quick look)

Args
```json
{"file_path": "docs/old.md"}
```

Typed
```json
{ "path": "docs/old.md", "summary": "Deleted file docs/old.md" }
```

Legacy
```
Deleted file docs/old.md
```

### Simple call
```
delete_file(file_path="docs/note.md")
```

See also: [Typed Results vs Legacy Outputs](typed_results.md).

## Troubleshooting
- Sandbox error — Switch to store mode (`INSPECT_AGENTS_FS_MODE=store`) for delete operations.
- File did not exist — The response notes idempotent behavior and continues.

## Source of Truth
- Code: src/inspect_agents/tools_files.py (execute_delete), src/inspect_agents/tools.py (delete_file wrapper)
- See also: [files](files.md) (unified files tool)

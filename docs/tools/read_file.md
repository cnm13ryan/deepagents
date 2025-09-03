---
title: "read_file Reference"
status: draft
kind: builtin
mode: stateless
owner: docs
---

# read_file

## Overview
- Reads a file and returns cat‑style numbered lines (left‑padded line numbers plus a tab) with per‑line truncation.
- Use to inspect code/docs with controllable line ranges.
- Classification: stateless.

## Parameters
- file_path: string — Path to read. Required.
- offset: int — 0‑based starting line offset (default: 0).
 - limit: int — Maximum number of lines to return (default: 2000).
- instance: string — Optional `Files` instance name for isolation.

## Result Schema
- Default: string — Joined, numbered lines (each line truncated to 2000 chars before numbering). Empty files return the message: “System reminder: File exists but has empty contents”.
- Typed (when `INSPECT_AGENTS_TYPED_RESULTS=1`): `{ lines: list[string], summary: string }` (`FileReadResult`).

### Typed Results vs Legacy Outputs
- Env toggle: Set `INSPECT_AGENTS_TYPED_RESULTS=1` to return typed result models; when unset/false, the tool returns the legacy string.  
  Internally, the toggle is read from the `INSPECT_AGENTS_TYPED_RESULTS` environment variable.
- `FileReadResult.lines`: Cat-style formatted lines, not raw file lines. Each element is left‑padded with a 6‑wide line number, then a tab, then the (possibly truncated) line text. Numbers start at `offset + 1`. Example format: `"     1\tfirst line"`.
- `FileReadResult.summary`: Short, human‑readable status such as the count and range of lines read. In sandbox mode the summary notes sandbox usage; in store mode it includes the concrete line range (e.g., `lines 1-200`).
- Legacy string (no typed results): A single string containing the same formatted, numbered lines joined by newlines.
- Empty file behavior: Typed → `lines=[]` with a summary of the empty‑file reminder; Legacy → that reminder as a plain string.

## Timeouts & Limits
- Execution timeout: 15s by default; configurable via `INSPECT_AGENTS_TOOL_TIMEOUT` (seconds).
- Per‑line cap: 2000 characters per line before numbering.

## Sandbox Notes
- When `INSPECT_AGENTS_FS_MODE=sandbox` and sandbox is available, routes to `text_editor('view', path, view_range=[start,end])`. If sandbox is unavailable, falls back to the in‑memory store.
- Paths are not validated against traversal; rely on sandbox isolation when using untrusted input.
- Delete is not available in sandbox mode (applies to file tools generally); use store‑mode `delete_file` if needed.

## Examples
### Typed vs Legacy

Args
```json
{"file_path": "README.md", "offset": 0, "limit": 3}
```

Typed (INSPECT_AGENTS_TYPED_RESULTS=1)
```json
{
  "lines": [
    "     1\t# Project Title",
    "     2\t",
    "     3\tWelcome to the repo."
  ],
  "summary": "Read 3 lines from README.md (lines 1-3)"
}
```

Legacy (unset/false)
```
     1	# Project Title
     2	
     3	Welcome to the repo.
```

Empty file
```json
// Typed
{ "lines": [], "summary": "System reminder: File exists but has empty contents" }

// Legacy
"System reminder: File exists but has empty contents"
```

See also: [Typed Results vs Legacy Outputs](typed_results.md).

## Troubleshooting
- File not found — Check `file_path` spelling and the active `instance`.
- Offset beyond EOF — You’ll receive a clear error indicating the index and file length.

## Source of Truth
- Code: src/inspect_agents/tools_files.py (execute_read), src/inspect_agents/tools.py (read_file wrapper)
- Guides: ../guides/tool-umbrellas.md
- See also: [files](files.md) (unified files tool)

---
title: "files Reference (Unified)"
status: draft
kind: builtin
mode: stateless
owner: docs
---

# files (Unified File Operations)

## Overview
- Unified file operations via a single tool using a discriminated union for commands: `ls`, `read`, `write`, `edit`, `delete`.
- Prefer this tool in new prompts and configs; wrapper tools remain for backward compatibility.
- Classification: stateless.

## Parameters
- params: union — One of:
  - LsParams: `{ command: "ls", instance?: string }`
  - ReadParams: `{ command: "read", file_path: string, offset?: int, limit?: int, instance?: string }`
  - WriteParams: `{ command: "write", file_path: string, content: string, instance?: string }`
  - EditParams: `{ command: "edit", file_path: string, old_string: string, new_string: string, replace_all?: bool, instance?: string }`
  - DeleteParams: `{ command: "delete", file_path: string, instance?: string }`

## Result Schema
- Depends on the command:
  - ls → default: list[string]; typed: `{ files: list[string] }` (`FileListResult`).
  - read → default: string of numbered lines; typed: `{ lines: list[string], summary: string }` (`FileReadResult`).
  - write → default: string; typed: `{ path: string, summary: string }` (`FileWriteResult`).
  - edit → default: string; typed: `{ path: string, replaced: int, summary: string }` (`FileEditResult`).
  - delete → default: string; typed: `{ path: string, summary: string }` (`FileDeleteResult`).

See also: [Typed Results vs Legacy Outputs](typed_results.md) for examples and the `INSPECT_AGENTS_TYPED_RESULTS` toggle.

## Timeouts & Limits
- Execution timeout: 15s by default (overridable via `INSPECT_AGENTS_TOOL_TIMEOUT`).
- Read caps: default `limit=2000` lines; per-line truncation 2000 characters.
- No explicit hard cap for write/edit sizes in store mode.

## Sandbox vs Store
- When `INSPECT_AGENTS_FS_MODE=sandbox` and sandbox is available:
  - read/edit/write route to `text_editor` operations; `ls` proxies to a shell `ls -1` via sandbox.
  - delete is intentionally disabled and will raise an error.
- When sandbox is unavailable or `store` mode is active, operations use the in‑memory `Files` store.

## Examples
```json
// List files
{"params": {"command": "ls"}}

// Read first 200 lines
{"params": {"command": "read", "file_path": "docs/README.md", "offset": 0, "limit": 200}}

// Write a file
{"params": {"command": "write", "file_path": "docs/note.md", "content": "Hello"}}

// Edit once
{"params": {"command": "edit", "file_path": "pyproject.toml", "old_string": "0.1.0", "new_string": "0.1.1"}}

// Delete (store mode only)
{"params": {"command": "delete", "file_path": "docs/note.md"}}
```

## Config Keys
- INSPECT_AGENTS_TOOL_TIMEOUT — per-call timeout in seconds (default 15).
- INSPECT_AGENTS_TYPED_RESULTS — `1/true` to enable typed result models.
- INSPECT_AGENTS_FS_MODE — `store` (default) | `sandbox` to use host editor tools.

## Source of Truth
- Code: src/inspect_agents/tools_files.py (`files_tool`, `execute_*`)
- Types: src/inspect_agents/tool_types.py (`FilesToolParams`)
- Wrappers: [read_file](read_file.md), [write_file](write_file.md), [edit_file](edit_file.md), [ls](ls.md), [delete_file](delete_file.md)

---
title: "update_todo_status Reference"
status: draft
kind: builtin
mode: stateless
owner: docs
---

# update_todo_status

## Overview
- Updates the status of a single TODO item with validated transitions; returns a summary string or a typed payload.
- Allowed transitions: `pending -> in_progress -> completed`. Direct `pending -> completed` requires an explicit flag (see parameters).
- Classification: stateless.

## Parameters
- todo_index: int — Index of the todo to update (0‑based). Required.
- status: "pending" | "in_progress" | "completed" — Target status. Required.
- allow_direct_complete: bool — Permit `pending -> completed` directly; logs a warning when used (default: false).

## Result Schema
- Default: string — JSON text with `ok: true` and `message`, and optional `meta.warning` when direct completion is allowed.
- Typed (when `INSPECT_AGENTS_TYPED_RESULTS=1`): `{ index: int, status: string, warning: string | null, summary: string }` (`TodoStatusResult`).

## Timeouts & Limits
- Execution timeout: 15s.

## Examples
```
# Mark the second item in progress
update_todo_status(todo_index=1, status="in_progress")

# Directly complete the first item (logs a warning)
update_todo_status(todo_index=0, status="completed", allow_direct_complete=true)
```

## Safety & Best Practices
- Indices are 0‑based; validate the current TODO list before updating.

## Troubleshooting
- Invalid status — Use one of: `pending`, `in_progress`, `completed`.
- Index error — Ensure `todo_index` is within range of the current list.

## Source of Truth
- Code: src/inspect_agents/tools.py (`update_todo_status`)
- Types: src/inspect_agents/tool_types.py (`UpdateTodoStatusParams`)

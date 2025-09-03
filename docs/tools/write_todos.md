---
title: "write_todos Reference"
status: draft
kind: builtin
mode: stateless
owner: docs
---

# write_todos

## Overview
- Writes the complete TODO list to the shared in‑memory Todos store.
- Accepts structured items and performs light coercion for convenience.
- Classification: stateless.

## Parameters
- todos: list[TodoItem] — Required. Each item is `{ content: string, status: "pending" | "in_progress" | "completed" }`.
  - Permissive coercion: string‑like inputs are accepted and stored as `{ content: <string>, status: "pending" }`.

## Result Schema
- Default: string — Summary message (e.g., “Updated todo list to [...]”).
- Typed (when `INSPECT_AGENTS_TYPED_RESULTS=1`): `{ count: int, summary: string }` (`TodoWriteResult`).

## Timeouts & Limits
- Execution timeout: 15s by default; configurable via `INSPECT_AGENTS_TOOL_TIMEOUT` (seconds).

## Examples
```
# Minimal strings are coerced to TodoItem with pending status
write_todos(todos=["Draft web_search prompts", "Prep bash compile command"]) 

# Structured items with explicit statuses
write_todos(todos=[
  {"content": "Write API tests", "status": "in_progress"},
  {"content": "Ship docs", "status": "completed"}
])
```

## Safety & Best Practices
- Keep items concise; prefer imperative phrasing.

## Troubleshooting
- Invalid payload — Ensure `todos` is a JSON array of strings or structured `TodoItem` objects.

## Source of Truth
- Code: src/inspect_agents/tools.py (`write_todos`)
- Types: src/inspect_agents/tool_types.py (`TodoItem`, `WriteTodosParams`)

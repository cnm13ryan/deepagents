---
title: "write_todos Reference"
status: draft
kind: builtin
mode: stateless
owner: docs
---

# write_todos

## Overview
- Writes the complete TODO list to the shared in-memory Todos store for this run.
- Use to capture or refresh the backlog of next actions.
- Classification: stateless (no retained process/session state between calls).

## Parameters
- todos: list[str] — Items to set or add (see code for exact behavior). Required.

## Result Schema
- items: list[str] — Current TODO list after write.
- errors: list[str] — Validation messages if present.

## Timeouts & Limits
- Execution timeout: TBD.
- Size limits: TBD (see implementation for truncation behavior).

## Examples
### Agent prompt snippet
```
Use write_todos to record: ["Draft web_search prompts", "Prep bash compile command"].
```

### Failure case
> Symptom: item too long (>500 chars)
> Fix: shorten or split into multiple items.

## Safety & Best Practices
- Keep items concise; prefer imperative phrasing.

## Troubleshooting
- Message: invalid payload — Ensure `todos` is a JSON array of strings.

## Source of Truth
- Code: src/inspect_agents/tools.py (builtin helpers)
- Guides: ../guides/tool-umbrellas.md

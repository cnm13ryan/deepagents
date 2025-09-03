---
title: "update_todo_status Reference"
status: draft
kind: builtin
mode: stateless
owner: docs
---

# update_todo_status

## Overview
- Updates the status of a single TODO item with validated transitions; returns JSON payload.
- Use to mark items as todo/in-progress/done or similar states.
- Classification: stateless (no retained process/session state between calls).

## Parameters
- item: string — The TODO text or id. Required.
- status: string — Target status. Required.

## Result Schema
- item: string — The affected item.
- status: string — The resulting status.
- errors: list[str] — Validation errors if transition not allowed.

## Timeouts & Limits
- Execution timeout: TBD.

## Examples
```
Use update_todo_status to set "Draft web_search prompts" to done.
```

## Safety & Best Practices
- Prefer id-based addressing when available to avoid accidental mismatches.

## Troubleshooting
- Message: invalid status — Use a supported value.

## Source of Truth
- Code: src/inspect_agents/tools.py
- Guides: ../guides/tool-umbrellas.md


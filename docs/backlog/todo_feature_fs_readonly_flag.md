# TODO: Filesystem Sandbox — Enforce Read‑Only Mode Flag

## Context & Motivation
- Purpose: provide a sandbox read‑only mode that blocks writes/edits/deletes to host FS.
- Problem: sandbox currently allows write/edit (delete disabled) with no repo‑wide read‑only switch.
- Value: safer demos/prod where the host filesystem must not be mutated.
- Constraints: only affect sandbox mode; store mode semantics unchanged.

## Implementation Guidance
- Examine: `src/inspect_agents/tools_files.py` (execute_write/edit/delete), `src/inspect_agents/tools.py` (`_use_sandbox_fs()`), unit tests in `tests/unit/inspect_agents/`.
- Grep tokens: `execute_write(`, `execute_edit(`, `execute_delete(`, `_use_sandbox_fs(`, `INSPECT_AGENTS_FS_MODE`.
- Existing pattern: delete is disabled in sandbox with a structured `ToolException` and `tool_event` error log.

## Scope Definition
- Implement: honor `INSPECT_AGENTS_FS_READ_ONLY=1` by raising `ToolException` in `execute_write`, `execute_edit`, and `execute_delete` when `_use_sandbox_fs()` is true; emit `tool_event ... phase="error"` with code `Readonly`.
- Preserve: behavior in store mode.
- Tests: parametrize sandbox write/edit/delete with env set; assert exception and no editor calls performed.

## Success Criteria
- Behavior: sandbox write/edit/delete are blocked when env flag is set; delete remains blocked even without flag (status quo).
- Tests: new tests added pass; existing FS tests remain green.
- Docs: ADR 0004 and tools docs updated to mention the read‑only flag.

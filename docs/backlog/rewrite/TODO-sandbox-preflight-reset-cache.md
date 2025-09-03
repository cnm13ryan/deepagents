# TODO — Reset Preflight Cache API

## Context & Motivation
- Purpose: allow long-lived processes and tests to re-evaluate sandbox availability when environment changes mid-run.
- Problem: sticky process-wide cache can become stale (e.g., sandbox comes online; stubs installed/removed during tests).
- Impact: better test control and operational recovery without background timers.
- Constraints: minimal surface area; no timers/threads; keep default behavior unchanged.

## Implementation Guidance
- Files to examine:
  - `src/inspect_agents/tools_files.py` — cache variables `_SANDBOX_READY`, `_SANDBOX_WARN`; helper `_ensure_sandbox_ready`. 〖F:src/inspect_agents/tools_files.py†L20-L38〗 〖F:src/inspect_agents/tools_files.py†L25-L89〗
  - `src/inspect_agents/tools.py` — `_log_tool_event` for structured logs. 〖F:src/inspect_agents/tools.py†L56-L79〗
- Greppables: `_SANDBOX_READY`, `_SANDBOX_WARN`, `_ensure_sandbox_ready(`, `files:sandbox_preflight`.
- Suggested shape:
  - `async def reset_sandbox_preflight() -> None:` clears cache; optional `anyio.Lock` to prevent races.
  - Emit one info log via `_log_tool_event(name="files:sandbox_preflight", phase="info", extra={"action":"reset"})`.

## Scope Definition
- Add the reset function in `src/inspect_agents/tools_files.py`; export if module uses `__all__` (none currently).
- No changes to call sites; intended for tests/host apps to import and call.
- Avoid TTL or periodic rechecks in this task (covered by a separate TODO).

## Success Criteria
- Tests (new):
  - Start with unavailable sandbox → next call marks unavailable; install stubs in `sys.modules` → call `reset_sandbox_preflight()` → subsequent call uses sandbox path.
  - Reverse direction (stubs → remove → reset) yields Store fallback.
- No regressions in default flows; no additional hot-path cost.


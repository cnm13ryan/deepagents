# TODO — TTL-Based Recheck for Sandbox Availability (Optional)

## Context & Motivation
- Purpose: let long-lived processes self-heal if the sandbox appears later (e.g., sidecar starts up) without manual reset.
- Problem: sticky cache never rechecks; operational changes require restarts or manual reset.
- Impact: improved robustness with bounded complexity.
- Constraints: on-demand only (no background loops); minimal overhead; preserve stubbing behavior.

## Implementation Guidance
- Files to examine:
  - `src/inspect_agents/tools_files.py` — extend `_ensure_sandbox_ready` with TTL logic; add `_SANDBOX_READY_TS: float | None` and an `anyio.Lock`. 〖F:src/inspect_agents/tools_files.py†L25-L38〗 〖F:src/inspect_agents/tools_files.py†L25-L89〗
- Greppables: `_ensure_sandbox_ready(`, `_SANDBOX_READY`, `_SANDBOX_WARN`.
- Proposed behavior:
  - New env `INSPECT_SANDBOX_PREFLIGHT_TTL=<seconds>`.
    - Unset: current sticky behavior.
    - `0`: recheck on every call.
    - `>0`: recheck when `now - _SANDBOX_READY_TS >= TTL`.
  - On availability flip, emit one-time info log `files:sandbox_preflight phase=status_changed` with `old`/`new` fields.
  - Continue honoring test stubs short-circuit before invoking helper.

## Scope Definition
- Contained changes to `_ensure_sandbox_ready`; do not modify callers.
- No timers/threads; just timestamp/branching logic.

## Success Criteria
- Manual validation: simulate missing → stubs appear; with small TTL, next call after TTL flips to available; status-changed log emitted once.
- Default behavior unchanged when env unset.


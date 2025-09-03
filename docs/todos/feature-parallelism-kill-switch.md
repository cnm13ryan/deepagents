# TODO — Global Kill‑Switch to Disable Parallel Tool Calls

Status: Planned • Owner: TBA • Priority: Medium

## Context & Motivation
- Purpose: Provide an operational safety switch to force serial execution for tool calls, even when marked parallel‑safe.
- Problem: During incidents/debugging, parallel execution can obscure root causes or trigger races; ops needs a one‑flag fallback.
- User impact: Faster incident mitigation and deterministic behavior when needed.
- Constraints: Default remains parallel enabled; per‑tool `parallel=False` (e.g., handoff) continues to be authoritative.

## Implementation Guidance
- Files:
  - `external/inspect_ai/src/inspect_ai/model/_call_tools.py` — function `disable_parallel_tools(...)`.
  - `external/inspect_ai/src/inspect_ai/model/_model.py` — `Model.generate(...)` sets `config.parallel_tool_calls=False` when `disable_parallel_tools(...)` returns True.
- Change:
  - Extend `disable_parallel_tools(...)` to also return True when `INSPECT_DISABLE_TOOL_PARALLEL` is truthy (`1`, `true`, etc.).
  - Keep existing behavior (return True if any tool’s `ToolDef.parallel` is False).
- Greppable anchors: `def disable_parallel_tools(`, `config.parallel_tool_calls = False`.

## Scope Definition
- In scope: Env‑flag check in `disable_parallel_tools(...)` to force serial.
- Out of scope: Provider/model API changes; conversation/transcript changes.
- Likely files modified: `_call_tools.py` only.

## Success Criteria
- With `INSPECT_DISABLE_TOOL_PARALLEL=1`, `Model.generate(...)` disables parallel tool calls; behavior remains otherwise unchanged.
- Tests verify the flag path is exercised (see tests TODO).

---

### Checklist
- [ ] Import `os` and parse truthy env var `INSPECT_DISABLE_TOOL_PARALLEL` in `disable_parallel_tools(...)`.
- [ ] Return True if flag is set (short‑circuit), else fall back to existing per‑tool checks.
- [ ] Add/adjust tests to exercise the flag path.


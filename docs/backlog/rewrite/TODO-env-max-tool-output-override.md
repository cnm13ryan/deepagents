# TODO — Env Override `INSPECT_MAX_TOOL_OUTPUT` (low precedence)

## Context & Motivation
- Purpose: Allow ops/CI to tune truncation fleet‑wide without code changes while keeping explicit per‑run settings authoritative.
- Problem: Teams occasionally need coarse controls for cost/latency; today only code/config changes can adjust limits.
- User Impact: Faster experiments and rollouts; must be low precedence to avoid surprising local runs.

## Implementation Guidance
- Examine:
  - `external/inspect_ai/src/inspect_ai/model/_call_tools.py` — `truncate_tool_output` (place env resolution where `active_generate_config().max_tool_output` is None).
  - `external/inspect_ai/src/inspect_ai/model/_generate_config.py` — update field docstring to mention env override and precedence.
- Grep targets: `truncate_tool_output(`, `active_generate_config().max_tool_output`, `INSPECT_MAX_TOOL_OUTPUT`, `warn_once(`.
- Approach:
  - Precedence: explicit arg `max_output` > `GenerateConfig.max_tool_output` > env `INSPECT_MAX_TOOL_OUTPUT` > fallback 16 KiB.
  - Parse env as integer bytes; invalid/negative → ignore; `0` means “no truncation”.
  - Optional: log once when env is used (see one‑time log feature).

## Scope Definition
- Implement:
  - In `truncate_tool_output`, if config value is None, read env and apply if valid.
  - Keep existing fallback to 16 KiB.
- Modify:
  - `external/inspect_ai/src/inspect_ai/model/_call_tools.py`
  - `external/inspect_ai/src/inspect_ai/model/_generate_config.py` (docstring only)
- Avoid:
  - Touching provider/model adapters; keep logic centralized in `truncate_tool_output`.

## Success Criteria
- Behavior: With only env set (no arg/config), payload between `<START/END>` is exactly the env byte count.
- Precedence: Passing `max_output` or setting per‑run `GenerateConfig.max_tool_output` overrides the env.
- Tests:
  - New integration test: monkeypatch env to N; assert payload == N. Then pass `max_output=M`; assert payload == M.

## Task Checklist
- [ ] Implement env resolution and validation in `truncate_tool_output`.
- [ ] Update GenerateConfig field docs with precedence and env name.
- [ ] Add integration test for env behavior and precedence.
- [ ] Run `pytest -q -k truncation` and ensure green.


# TODO — Default `max_tool_output = 16 KiB`

## Context & Motivation
- Purpose: Make the default tool-output byte limit explicit at the config layer to prevent oversized tool results from inflating prompts and costs.
- Problem: `GenerateConfig.max_tool_output` currently defaults to `None`; the effective limit comes from a fallback inside `truncate_tool_output`, which is less discoverable for users.
- User Impact: Clear, predictable guardrail across runs without requiring per-run overrides; low blast radius because the runtime already falls back to 16 KiB.
- Background: Limit resolution path is `truncate_tool_output(…)` → `active_generate_config().max_tool_output` → fallback 16 KiB. See:
  - `external/inspect_ai/src/inspect_ai/model/_call_tools.py` (limit resolution and envelope)
  - `external/inspect_ai/src/inspect_ai/model/_generate_config.py` (GenerateConfig field)

## Implementation Guidance
- Examine:
  - `external/inspect_ai/src/inspect_ai/model/_generate_config.py` — field: `max_tool_output: int | None = Field(default=None)` (set to `16 * 1024`).
  - `external/inspect_ai/src/inspect_ai/model/_call_tools.py` — function: `truncate_tool_output` (keep existing fallback and envelope).
  - `tests/integration/inspect_agents/test_truncation.py` — reference for envelope and byte-limit assertions.
- Grep targets: `GenerateConfig.max_tool_output`, `truncate_tool_output`, `active_generate_config`.
- Pattern: Keep function-level fallback to 16 KiB for defense in depth; make config default explicit; do not change envelope markers or truncation algorithm.
- Related deps: Pydantic `BaseModel`, `Field` (already in use).

## Scope Definition
- Implement:
  - Set `GenerateConfig.max_tool_output` default to `16 * 1024`.
  - Update field docstring to mention the default and that a per-run override or arg can change/disable it (arg `max_output=0` disables truncation for that call).
- Modify:
  - `external/inspect_ai/src/inspect_ai/model/_generate_config.py` only.
- Avoid:
  - Changing conversation truncation (`truncation` param in agents/react) or middle-truncation algorithm/envelope markers.

## Success Criteria
- Behavior: Without passing `max_output` or per-run `GenerateConfig`, oversized tool outputs truncate to exactly 16384 bytes inside `<START_TOOL_OUTPUT>…<END_TOOL_OUTPUT>`.
- Tests:
  - Add a new smoke test (see separate TODO for default-limit test) or extend existing tests to validate the default when not provided explicitly.
- Compatibility: No regressions; existing envelope tests still pass.

## Task Checklist
- [ ] Set default `max_tool_output = 16 * 1024` in GenerateConfig.
- [ ] Update inline docs for the field.
- [ ] Add/adjust test to assert default limit applies with no explicit max.
- [ ] Run `pytest -q -k truncation` and ensure green.


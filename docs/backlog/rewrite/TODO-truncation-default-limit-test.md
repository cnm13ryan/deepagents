# TODO — Add Default-Limit Smoke Test (no explicit max)

## Context & Motivation
- Purpose: Ensure the config‑layer default applies when no explicit limit is provided, catching regressions early.
- Problem: Existing tests validate explicit `max_output`; a default‑path test guards future refactors.
- User Impact: Stable, predictable behavior across providers and environments.

## Implementation Guidance
- Examine:
  - `tests/integration/inspect_agents/test_truncation.py` — pattern for constructing `long_output_tool` and extracting payload.
- Grep targets: `ChatMessageTool`, `execute_tools(`, `<START_TOOL_OUTPUT>`.
- Approach:
  - Create new test that omits `max_output` and asserts payload bytes == 16384 (16 KiB) given oversized tool output.

## Scope Definition
- Implement:
  - New file: `tests/integration/inspect_agents/test_truncation_default_limit.py`.
  - Reuse the same helper pattern as the existing truncation test.
- Modify:
  - Tests only; do not change runtime code.
- Avoid:
  - Altering existing truncation tests or external Inspect tests.

## Success Criteria
- Behavior: Test passes locally/offline with `NO_NETWORK=1`.
- Tests:
  - `pytest -q -k truncation` shows all truncation tests green, including the new default‑limit test.

## Task Checklist
- [ ] Implement new test without passing `max_output`.
- [ ] Assert payload length is exactly `16 * 1024` bytes.
- [ ] Run the truncation test subset and ensure green.


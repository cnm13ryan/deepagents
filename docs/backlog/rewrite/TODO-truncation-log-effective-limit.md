# TODO — One-time Log: Effective Tool-Output Limit and Source

## Context & Motivation
- Purpose: Improve observability by logging how the effective limit was chosen the first time truncation occurs (source: arg/config/env/default).
- Problem: When truncation is observed, the origin of the limit isn’t obvious; debugging requires code reading.
- User Impact: Faster diagnosis across environments and CI; minimal noise via one-time logging.

## Implementation Guidance
- Examine:
  - `external/inspect_ai/src/inspect_ai/model/_call_tools.py` — `truncate_tool_output`; use `warn_once(logger, ...)` pattern already present in this module.
- Grep targets: `warn_once(`, `logger = getLogger(__name__)`, `truncate_tool_output(`.
- Approach:
  - Compute `source` string: `arg` (explicit), `config`, `env` (if used), else `default`.
  - On first truncation, log once: `Tool output truncated to {bytes} (source: {source}).`

## Scope Definition
- Implement:
  - Add log emission guarded by a one-time mechanism (reuse `warn_once`).
- Modify:
  - `external/inspect_ai/src/inspect_ai/model/_call_tools.py` only.
- Avoid:
  - Logging at model init; tie logging to real truncation events.

## Success Criteria
- Behavior: A single log line on first truncation per run; no duplicate logs.
- Tests (optional):
  - Unit test capturing logs to assert a single record; acceptable to verify manually if log capture is brittle in CI.

## Task Checklist
- [ ] Determine `source` and emit one-time log within `truncate_tool_output`.
- [ ] (Optional) Add a log-capture test to assert single emission.
- [ ] Verify logs appear once under `pytest -q -k truncation` when truncation occurs.


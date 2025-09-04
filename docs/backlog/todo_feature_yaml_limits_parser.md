# TODO: YAML Limits — Parse and Return Inspect Limits

## Context & Motivation
- Purpose: make YAML `limits` actionable by returning Inspect `Limit` objects from the config path.
- Problem: YAML field exists but is ignored; `run_agent` already accepts `limits`.
- Value: first‑class control of time/message/token caps from config.

## Implementation Guidance
- Examine: `src/inspect_agents/config.py` (parse in `build_from_config`), `src/inspect_agents/run.py` (already passes `limits`), Inspect APIs in `external/inspect_ai/src/inspect_ai/util/_limit.py`.
- Grep tokens: `limits: list[Any] | None`, `build_from_config(`, `time_limit`, `message_limit`, `token_limit`.
- Minimal schema proposal: `[{"time": 600}, {"message": 200}, {"token": 50000}]`.

## Scope Definition
- Implement: map YAML entries to `time_limit()`, `message_limit()`, `token_limit()`; return in the 3‑tuple from `load_and_build` so callers can pass them to `run_agent`.
- Preserve: backward compatibility (empty or unknown entries ignored with a warning).
- Tests: YAML string load builds limits; a tiny run triggers a small message limit.

## Success Criteria
- Behavior: runs end on configured limits with expected error classes.
- Tests: new unit tests pass; existing remain green.

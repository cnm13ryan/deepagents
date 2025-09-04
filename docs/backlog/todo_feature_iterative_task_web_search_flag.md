# TODO: Iterative Task (Inspect) — `enable_web_search` Flag

## Context & Motivation
- Purpose: parity with local runner flag; simple way to enable search for the iterative task.
- Problem: `examples/research/iterative_task.py` exposes only `enable_exec`.
- Value: easier demos/tests; fewer env steps.

## Implementation Guidance
- Examine: `examples/research/iterative_task.py`.
- Grep tokens: `enable_exec`, `INSPECT_ENABLE_EXEC`, `os.environ`.

## Scope Definition
- Implement: add `enable_web_search: bool = False`; when true, set `INSPECT_ENABLE_WEB_SEARCH=1` before building agent.
- Tests: simple test asserts env present during task build (no network needed).

## Success Criteria
- Behavior: flag sets env and includes `web_search` when providers configured.
- Docs: update usage in file header.

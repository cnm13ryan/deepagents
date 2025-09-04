# TODO: Iterative Agent — Env Fallbacks for Time/Steps

Status: DONE (2025-09-04)
- Implemented: when constructor args are None, the agent reads `INSPECT_ITERATIVE_TIME_LIMIT` and `INSPECT_ITERATIVE_MAX_STEPS` with sane normalization.
  - Code: `src/inspect_agents/iterative.py` (env fallback parsing).
- Tests: `tests/unit/inspect_agents/iterative/test_iterative_limits.py` includes env fallback cases.

## Context & Motivation
- Purpose: allow environments to set default budgets without code changes.
- Problem: builder doesn’t read env; only runners set flags.
- Value: uniform control across local/CI/prod.

## Implementation Guidance
- Examine: `src/inspect_agents/iterative.py` (builder args `real_time_limit_sec`, `max_steps`).
- Grep tokens: `real_time_limit_sec`, `max_steps`.

## Scope Definition
- Implement: if args are None, read `INSPECT_ITERATIVE_TIME_LIMIT` and `INSPECT_ITERATIVE_MAX_STEPS`; clamp to sensible minimums.
- Tests: unit tests set env and assert applied values.

## Success Criteria
- Behavior: env fallbacks honored; explicit args still win.
- Tests: pass offline.

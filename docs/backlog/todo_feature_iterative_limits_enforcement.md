# TODO: Iterative Agent — In‑Loop Sample Limits Enforcement (message/token soft stop)

Status: DONE (2025-09-04)
- Implemented: agent-level `message_limit` and `token_limit` soft stops add a final explanatory message and stop the loop.
  - Code: `src/inspect_agents/iterative.py` (limit checks at top of loop, token estimation).
- Tests: `tests/unit/inspect_agents/iterative/test_iterative_soft_limits.py` covers message/token stop behavior.

## Context & Motivation
- Purpose: Provide clear, early termination when local message/token budgets are exceeded, independent of external runner limits, with a user-visible reason.
- Problem: The iterative loop does not enforce `message_limit`/`token_limit`; only runner-level limits can enforce them.
- Value: Predictable behavior and clearer logs during long runs.

## Implementation Guidance
- Examine:
  - `src/inspect_agents/iterative.py` — main loop top and progress pings.
  - `src/inspect_agents/run.py` — how external `limits` are passed/propagated (for reference only).
- Grep:
  - `while True:`, `progress_every`, `state.messages`, `model_length`.
- Steps:
  1) Extend `build_iterative_agent` with optional args: `message_limit: int | None = None`, `token_limit: int | None = None`.
  2) At the start of each loop iteration:
     - If `message_limit` and `len(state.messages) >= message_limit`: append a final user message `[limit] Message limit reached (N). Stopping.` and `break`.
     - If `token_limit`: either approximate tokens via `tiktoken` (preferred) or a simple heuristic; on overflow, append `[limit] Token budget reached (~M). Stopping.` and `break`.
  3) Keep defaults None to preserve current behavior; document precedence with runner limits.

## Scope Definition
- Iterative agent only; no change to submit-style supervisor.
- Do not raise internal Inspect exceptions; perform a soft stop with a final explanatory message.

## Success Criteria
- Behavior: With `message_limit=100`, the loop stops exactly when the 100th message would be added; a final note is present in history.
- Testing: Unit tests simulate growth to thresholds; assert stop conditions and the final message.
- Compatibility: Runner-level limits remain compatible; agent-level limits generally trigger first when set.

# TODO — Limits & Truncation

Context & Motivation
- Prevent runaway loops/costs and handle context overflows gracefully while keeping useful history.

Implementation Guidance
- Agent limits and continue behavior: `external/inspect_ai/src/inspect_ai/agent/_react.py`
- Solver defaults and message_limit behavior: `external/inspect_ai/src/inspect_ai/solver/_basic_agent.py`
- Truncation helpers: `external/inspect_ai/src/inspect_ai/model/_trim.py`

Scope — Do
- [ ] Choose default `message_limit` when `token_limit` is unset (e.g., 50)
- [ ] Enable truncation strategy (`truncation="auto"` or custom filter) for supervisor
- [ ] Provide explicit continue message for “no tool call” stalls
- [ ] Tests:
  - [ ] Force overflow to exercise truncation path and verify recovery or graceful stop
  - [ ] Verify message_limit termination includes transcript note

Scope — Don’t
- Don’t silently drop messages without informing the model (use truncation filters)

Success Criteria
- [ ] Overflow results in a controlled outcome (trim or terminate) with clear logs
- [ ] Limits configurable per agent; defaults documented

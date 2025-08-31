# TODO — Run Utility (execution helper)

Context & Motivation
- Provide a simple runner to execute the supervisor agent with string or message input, optional approval, and limits.

Implementation Guidance
- Read: Inspect agent runner `external/inspect_ai/src/inspect_ai/agent/_run.py`  
  Grep: `async def run(agent, input, limits=...)`
- If approvals are used, call `init_tool_approval(policies)` (from `inspect_ai.approval._apply`) before running the agent.
- For Solver‑style flows you can still use `external/inspect_ai/src/inspect_ai/solver/_run.py`.

- [ ] Add `src/inspect_agents/run.py` with:
  - [ ] `async def run_agent(agent: Agent, input: str|list[ChatMessage], approval: list[ApprovalPolicy]|None=None, limits: list[Limit]=[]) -> AgentState` that:
    - [ ] Calls `init_tool_approval(approval)` if provided
    - [ ] Delegates to `inspect_ai.agent.run(agent, input, limits=limits)`
  - [ ] Optionally provide `run_solver(solver, input)` for solver use cases
- [ ] Tests `tests/inspect_agents/test_run.py` covering str vs. message inputs and both agent types

Scope — Don’t
- Do not depend on external model endpoints in tests; use stubs/fakes

- [ ] Smoke E2E test passes returning an `AgentState` with new messages and non-empty `output`

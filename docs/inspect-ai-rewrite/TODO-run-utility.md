# TODO — Run Utility (execution helper)

Context & Motivation
- Provide a simple runner to execute the supervisor agent with string or message input, optional approval, and limits.

Implementation Guidance
- Read: Inspect solver runner `external/inspect_ai/src/inspect_ai/solver/_run.py`  
  Grep: `def run(`, `TaskState`

Scope — Do
- [ ] Add `src/inspect_agents/run.py` with:
  - [ ] `async def run_agent(agent: Solver|Agent, input: str|list[ChatMessage], approval: Approver|None=None, limits: ...) -> tuple[list[ChatMessage], ModelOutput|None]`
  - [ ] If `agent` is `Solver`, call Inspect `run`. If `Agent`, create `AgentState` and invoke.
- [ ] Tests `tests/inspect_agents/test_run.py` covering str vs. message inputs and both agent types

Scope — Don’t
- Do not depend on external model endpoints in tests; use stubs/fakes

Success Criteria
- [ ] Smoke E2E test passes returning new messages and non-empty output


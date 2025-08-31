# TODO — Migration Shim (`create_deep_agent` parity)

Context & Motivation
- Provide a drop-in `create_deep_agent(...)`-compatible API that builds Inspect-based supervisor + sub-agents + approval under the hood.

Implementation Guidance
- Read: `src/deepagents/graph.py`  
  Grep: `def create_deep_agent`, `builtin_tools`, `subagents`, `interrupt_config`

Scope — Do
- [ ] Add `src/inspect_agents/migration.py` with:
  - [ ] `def create_deep_agent(tools, instructions, model=None, subagents=None, state_schema=None, builtin_tools=None, interrupt_config=None, ...) -> Callable|Solver` mapping to Inspect
  - [ ] Internally: resolve built-ins (Store tools), build subagents (handoff), build supervisor (ReAct), build approval (policy)
- [ ] Tests `tests/inspect_agents/test_migration.py` verifying a minimal flow (todos + file write) works via shim

Scope — Don’t
- Do not change existing `src/deepagents/*`

Success Criteria
- [ ] Existing-style examples run via shim with equivalent outcomes


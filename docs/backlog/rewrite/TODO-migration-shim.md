# DONE — Migration Shim (`create_deep_agent` parity)

Context & Motivation
- Provide a drop-in `create_deep_agent(...)`-compatible API that builds Inspect-based supervisor + sub-agents + approval under the hood.

Implementation Guidance
- Read: `src/deepagents/graph.py`  
  Grep: `def create_deep_agent`, `builtin_tools`, `subagents`, `interrupt_config`

Scope — Do
- [x] Add `src/inspect_agents/migration.py` with:
  - [x] `def create_deep_agent(tools, instructions, model=None, subagents=None, state_schema=None, builtin_tools=None, interrupt_config=None, ...) -> Callable|Solver` mapping to Inspect
  - [x] Internally: resolve built-ins (Store tools), build subagents (handoff), build supervisor (ReAct), build approval (policy)
- [x] Tests `tests/unit/inspect_agents/test_migration.py` verifying a minimal flow (todos + file write) works via shim
 - [x] Quickstart example under `examples/inspect/`

Scope — Don’t
- Do not change existing `src/deepagents/*`

Success Criteria
- [x] Existing-style examples run via shim with equivalent outcomes

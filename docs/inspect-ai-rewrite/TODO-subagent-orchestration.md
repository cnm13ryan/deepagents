# TODO — Sub-agent Orchestration (handoff/as_tool)

Context & Motivation
- Recreate deepagents’ `task` delegation using Inspect handoff tools (`transfer_to_<name>`) and optional `as_tool` variants.

Implementation Guidance
- Read: `src/deepagents/sub_agent.py`  
  Grep: `SubAgent`, `_create_task_tool`, `subagent_type`, `tools_by_name`
- Read: Inspect: `agent/_handoff.py`, `agent/_as_tool.py`  
  Grep: `handoff(`, `as_tool(`, `transfer_to_`

Scope — Do
- [ ] In `src/inspect_agents/agents.py` add:
  - [ ] `def build_subagents(configs: list[SubAgentCfg], base_tools: list[Tool]) -> list[Tool]`
  - [ ] For each cfg, build Inspect agent with prompt/tools/model; expose `handoff(..., tool_name=f"transfer_to_{name}")`
- [ ] Tests `tests/inspect_agents/test_subagents.py`:
  - [ ] Supervisor calling `transfer_to_*` appends sub-agent messages and produces output
  - [ ] Verify shared store visibility (or use `store_as(..., instance=...)` if isolating)

Scope — Don’t
- Do not couple to LangGraph

Success Criteria
- [ ] Delegation works with named sub-agents and preserves conversation context


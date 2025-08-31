# TODO — Sub-agent Orchestration (handoff/as_tool)

Context & Motivation
- Recreate deepagents’ `task` delegation using Inspect handoff tools (`transfer_to_<name>`) and optional `as_tool` variants.

Implementation Guidance
- Read: `src/deepagents/sub_agent.py`  
  Grep: `SubAgent`, `_create_task_tool`, `subagent_type`, `tools_by_name`
- Read: Inspect: `agent/_handoff.py`, `agent/_as_tool.py`, and tool execution internals  
  Grep: `handoff(`, `as_tool(`, `transfer_to_`, `agent_handoff` (in `model/_call_tools.py`)
  Notes:
  - Handoff injects a boundary message: `Successfully transferred to <agent_name>.` and returns only new messages from the sub‑agent.
  - System messages from the sub‑agent are filtered from the returned messages; assistant messages are prefixed with the agent name.

Scope — Do
- [ ] In `src/inspect_agents/agents.py` add:
  - [ ] `def build_subagents(configs: list[SubAgentCfg], base_tools: list[Tool]) -> list[Tool]`
  - [ ] For each cfg, build Inspect agent with prompt/tools/model; expose `handoff(..., tool_name=f"transfer_to_{name}")`
- [ ] Tests `tests/inspect_agents/test_subagents.py`:
  - [ ] Assert a `ChatMessageTool` boundary exists with content `Successfully transferred to <agent_name>.`
  - [ ] Ensure only the sub‑agent’s new messages are appended (compare message IDs vs. pre‑handoff list)
  - [ ] Verify assistant messages from sub‑agent are prefixed with the agent name
  - [ ] Verify shared store visibility (or use `store_as(..., instance=...)` if isolating)

Scope — Don’t
- Do not couple to LangGraph

Success Criteria
- [ ] Delegation works with named sub-agents and preserves conversation context
- [ ] Default delegation uses `handoff()`; provide `as_tool()` mode for single-shot utilities via config (e.g., `mode: tool`)

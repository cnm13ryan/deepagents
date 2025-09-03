# DONE — Supervisor Agent (ReAct via Inspect)

Context & Motivation
- Implement the top-level agent using Inspect’s ReAct loop (submit-terminated), wiring built-in tools and user tools with a guiding base prompt.

Implementation Guidance
- Read: `src/deepagents/graph.py`  
  Grep: `base_prompt`, `create_deep_agent`, `built_in_tools`  
- Prefer Inspect `agent.react(...)` (adds a `submit` tool by default); avoid manually adding a second submit tool.
- Optionally use `AgentPrompt` to include a `handoff_prompt` if the supervisor will delegate frequently.

- [x] Add `src/inspect_agents/agents.py` with:
  - [x] `def build_supervisor(prompt: str, tools: list[Tool], attempts: int=1, limits: ...) -> Agent` that calls `react(prompt=..., tools=..., attempts=..., submit=True, ...)`
  - [x] Compose base prompt similar to deepagents’ `base_prompt`
  - [x] Configure limits/attempts; no manual submit wiring required
- [x] Tests in `tests/integration/inspect_agents/test_supervisor.py` verifying loop runs and terminates on submit

Scope — Don’t
- No sub-agent construction here (handled in separate feature)

Success Criteria
- [x] Supervisor executes tool loop and sets completion upon submit
- [ ] Configurable attempts/message/token limits work

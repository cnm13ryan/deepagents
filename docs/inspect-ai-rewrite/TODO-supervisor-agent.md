# TODO — Supervisor Agent (ReAct via Inspect)

Context & Motivation
- Implement the top-level agent using Inspect’s ReAct loop (submit-terminated), wiring built-in tools and user tools with a guiding base prompt.

Implementation Guidance
- Read: `src/deepagents/graph.py`  
  Grep: `base_prompt`, `create_deep_agent`, `built_in_tools`  
- Read: `external/inspect_ai/src/inspect_ai/solver/_basic_agent.py` for default ReAct loop

Scope — Do
- [ ] Add `src/inspect_agents/agents.py` with:
  - [ ] `def build_supervisor(prompt: str, tools: list[Tool], submit_name: str='submit', attempts: int=1, limits: ...) -> Solver|Agent`
  - [ ] Compose base prompt similar to deepagents’ `base_prompt`
  - [ ] Include submit tool and limits
- [ ] Tests in `tests/inspect_agents/test_supervisor.py` verifying loop runs and terminates on submit

Scope — Don’t
- No sub-agent construction here (handled in separate feature)

Success Criteria
- [ ] Supervisor executes tool loop and sets completion upon submit
- [ ] Configurable attempts/message/token limits work


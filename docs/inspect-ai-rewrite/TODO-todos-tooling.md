# done — TODO — Todos Tooling (Store-backed)

Context & Motivation
- Provide Inspect-native `write_todos` so agents can plan and track work with a persistent list.

Implementation Guidance
- Read: `src/deepagents/tools.py` current behavior  
  Grep: `def write_todos`, `ToolMessage`, `todos`
- Use Inspect `@tool` from: `external/inspect_ai/src/inspect_ai/tool/_tool.py`

Scope — Do
- [ ] Add/extend `src/inspect_agents/tools.py` with:
  - [ ] `@tool() def write_todos(todos: list[Todo]) -> str:` updates `Todos.todos` in Store; returns confirmation string
- [ ] Unit tests in `tests/inspect_agents/test_todos_tool.py`

Scope — Don’t
- No agent wiring here (done in Supervisor feature)

Success Criteria
- [ ] Invoking tool updates Store; subsequent read reflects changes
- [ ] Output string mirrors prior behavior (human-readable summary)

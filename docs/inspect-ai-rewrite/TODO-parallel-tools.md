# TODO — Tool Parallelism Policy

Context & Motivation
- Models may emit multiple tool_calls in one assistant turn; Inspect executes them concurrently except handoff tools. Concurrency impacts ordering and safety.

Implementation Guidance
- Tool execution: `external/inspect_ai/src/inspect_ai/model/_call_tools.py` (TaskGroup)
- Handoff is non-parallel by design: `agent/_handoff.py`

Scope — Do
- [x] Declare which tools are parallel-safe vs must-run-serially (handoff tools are serial)
- [x] Ensure handoff tools remain serial
- [ ] Tests:
  - [x] Emit two simple parallel-safe tool calls → both ChatMessageTool results present
  - [ ] Handoff tool issued with another tool → only handoff is handled; others deferred/cancelled as designed

Scope — Don’t
- Don’t rely on strict ordering between parallel tool results; document ordering expectations

Success Criteria
- [ ] Clear policy documented; test demonstrates concurrency without data races

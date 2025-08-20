# OpenAI Agents — Key Learnings for DeepAgents

Purpose: capture high‑leverage patterns from OpenAI Agents SDK and map them to concrete integrations in DeepAgents to accelerate fast prototyping of simple and powerful agentic systems.

## Summary of Key Patterns → DeepAgents Adoption

1) Strict, self‑documenting tools
- Pattern: Decorator `function_tool` derives JSON schema from function signature + docstring; strict JSON validation; dynamic enable/disable; graceful error shaping.
- Adopt in DeepAgents:
  - Provide `function_tool` decorator: builds strict schemas, supports `is_enabled` (bool/callable), and `failure_error_function` to return LLM‑legible errors instead of crashing.
  - Keep existing LangChain tools interoperable; offer this as the fast path for new tools.

2) Typed outputs and early stop behavior
- Pattern: Declare `output_type`; stop when model returns structured output. Configure `tool_use_behavior` (run again, stop on first tool, stop at named tools, or custom function).
- Adopt in DeepAgents:
  - Add optional `output_schema` to `create_deep_agent` and validate termination.
  - Add `tool_use_behavior` with: `run_llm_again` | `stop_on_first_tool` | `stop_at_tools=[...]` | custom callback.

3) Handoffs vs. sub‑agents (context transfer)
- Pattern: Handoffs transfer control and history; tools are one‑shot calls. Both are useful depending on context needs.
- Adopt in DeepAgents:
  - Keep current “task” sub‑agent (context quarantine).
  - Add an optional “handoff” mode that inherits message history for continuity, tracked explicitly in state.

4) Input/Output guardrails
- Pattern: Declarative input tripwires and final output validators; can block, annotate, or halt.
- Adopt in DeepAgents:
  - Add `input_guardrails` and `output_guardrails` to `create_deep_agent` with built‑ins (regex allow/deny, JSON schema validate, keyword tripwires).
  - On tripwire: emit a clear message; stop or re‑plan per config.

5) Session memory (pluggable)
- Pattern: Session protocol (e.g., SQLite) to maintain history across runs automatically.
- Adopt in DeepAgents:
  - Provide `Session` interface + `SQLiteSession` helper. Wire into `.invoke(..., session=...)` to auto‑hydrate messages.

6) Tracing, spans, and streamed events
- Pattern: Rich spans (agents/tools/guardrails) with error attachment; semantic stream events (tool_called, handoff, approvals).
- Adopt in DeepAgents:
  - Add TraceProvider abstraction (console/JSON). Emit structured events for tool calls, sub‑agent spawns, handoffs, guardrails, plan updates. Include privacy toggles.

7) Call‑before‑model hooks
- Pattern: `call_model_input_filter` mutates input just before model call (e.g., trim, add hints).
- Adopt in DeepAgents:
  - Add `before_model_call(state, messages) -> messages` hook for prompt surgery and token budget control.

8) Usage and cost tracking
- Pattern: Aggregate input/output tokens/time per turn and totals.
- Adopt in DeepAgents:
  - Capture usage per model call; roll up in final state; print a concise summary.

9) Hosted tools and approvals (MCP, shell, code, image)
- Pattern: First‑class hosted tools with optional approval callbacks.
- Adopt in DeepAgents:
  - Adapters for hosted MCP with approval, local shell with [DESTRUCTIVE] gating + approvals, and a sandboxed code interpreter (later).

10) Agent as Tool (agent‑as‑function)
- Pattern: Promote an agent to a tool with custom output extractors for reuse.
- Adopt in DeepAgents:
  - Provide `agent_as_tool(agent, name, desc)` to expose a sub‑graph as a callable tool.

11) Lifecycle hooks
- Pattern: Hooks for start/finish and per‑turn events.
- Adopt in DeepAgents:
  - Add before/after hooks for agent turn, tool call, handoff, finalize. Feed telemetry and guardrails.

## Prioritized Integration Plan

Quick wins (1–3 days):
- `function_tool` decorator with strict schemas and `is_enabled`.
- `output_schema` + `tool_use_behavior` early stop options.
- `before_model_call` hook for prompt trimming/injection.
- Token/time usage summary in state output.
- Emit structured events (console/JSON) for tool calls, subagent spawns, plan updates.

Near term (1–2 weeks):
- Guardrails: `input_guardrails`/`output_guardrails` with regex/JSON/keyword built‑ins.
- Session memory: `Session` protocol + `SQLiteSession`; optional LangGraph checkpointer integration.
- Agent‑as‑tool helper.
- Handoff mode (inherit history) alongside current quarantine sub‑agents.
- Tracing provider abstraction + privacy flags.

Later (as needed):
- Hosted MCP with approval; local shell + code interpreter via sandbox; image generation bridge.
- Model roles/provider routing; align with `init_chat_model`.

## Suggested API Surfaces (sketch)

- Tools: `from deepagents.tools import function_tool`
- Agent creation:
  - `create_deep_agent(..., output_schema=MyTypedDict, tool_use_behavior="stop_on_first_tool", input_guardrails=[...], output_guardrails=[...])`
  - `before_model_call` hook in config
  - `invoke(..., session=SQLiteSession("user123"))`
- Observability:
  - `from deepagents.trace import set_trace_provider(ConsoleTrace())`
  - `set_trace_privacy(model=False, tools=False)`
  - `agent.astream_events(...)` yields semantic events
- Composition:
  - `from deepagents.compose import agent_as_tool`

## Caveats
- Strict schemas require good docstrings; provide a helper to infer clean descriptions.
- Handoffs vs quarantine are complementary; expose modes clearly.
- Approvals first via console; Studio UI later.
- Structured outputs vary by provider; validate early and provide readable errors.

## Why This Accelerates Prototyping
- Faster scaffolding: write a function, decorate, ship.
- Safer loops: early stops, guardrails, approvals.
- Better observability: events/spans/usage shorten debug cycles.
- Reuse: sessions, handoffs, and agent‑as‑tool compose small parts into bigger systems quickly.

## Next Steps
- Implement `function_tool` and convert 1–2 built‑ins as examples.
- Add `tool_use_behavior` + `output_schema` with stop conditions.
- Add `before_model_call` and usage reporting; emit event stream.


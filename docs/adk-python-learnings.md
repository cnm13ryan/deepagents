# Google ADK (adk-python) — Key Learnings for DeepAgents

Purpose: extract high‑leverage patterns from Google’s Agent Development Kit (ADK) and map them to concrete integrations in DeepAgents to accelerate fast prototyping of simple and powerful agentic systems.

## Core Patterns → DeepAgents Adoption

- LLM Agent with rich configuration
  - Pattern: `LlmAgent` exposes instruction/global_instruction (string or callable), `sub_agents` composition, planners, code executors, strict input/output schemas, and transfer controls (disallow transfer to parent/peers). Output can be saved to a named state key via event actions.
  - Adopt:
    - Add global instructions (root-scoped) and per-agent instruction provider functions.
    - Add `output_schema` semantics: if set, disable tool use for that call and stop on valid structured output; support `output_key` to persist output into state.
    - Provide transfer controls and a simple “transfer_to_agent” tool (handoff) alongside our current quarantine-style sub-agent task.

- Flow selection (AutoFlow vs SingleFlow)
  - Pattern: choose a simple single-agent tool loop (no sub-agents) vs. an auto flow that permits agent transfer.
  - Adopt:
    - Provide a `flow_mode` option: `single` (no delegation) vs `auto` (allow sub-agents/handoffs), for quick scoping and simpler behavior when desired.

- Before/After hooks for model and tools
  - Pattern: callbacks before model call (can short-circuit) and after model call; before tool and after tool (can substitute outputs).
  - Adopt:
    - Add lightweight hooks: `before_model(state, llm_request)`, `after_model(state, llm_response)`, `before_tool(tool, args, ctx)`, `after_tool(tool, args, ctx, result)`. Default no‑ops. Log with trace events.

- Context control (include contents)
  - Pattern: `include_contents` controls whether prior history is injected or the model sees only current instruction/input.
  - Adopt:
    - Add per‑turn option to trim or exclude history; implement a `before_model_call` filter to enforce token budgets or “fresh‑context” calls.

- Planner integration
  - Pattern: planner instructs the agent to plan and execute step by step; supports model’s built‑in “thinking” via config.
  - Adopt:
    - Keep `write_todos` for planning visibility; add optional planner interface to auto-generate/update TODOs and interpret “thinking_config” when available.

- Code execution integration
  - Pattern: code executor (built‑in or custom) to run code emitted by the model; participates in the loop.
  - Adopt:
    - Add a sandboxed code executor tool (opt‑in) with approvals; later support model built‑ins via adapter.

- Tools and Toolsets
  - Pattern: `FunctionTool` wraps Python callables; toolsets generate tools (e.g., OpenAPI → RestApiTool list), MCP and Google Cloud tools, LangChain tool bridge, retrieval, artifact/memory utilities.
  - Adopt:
    - Provide `function_tool` decorator (strict schema) and a minimal OpenAPI toolset builder to auto‑generate tools from a spec.
    - Keep MCP via existing adapter; add credential/tool context patterns inspired by ADK’s `ToolContext`.

- Sessions, Events, and State Delta
  - Pattern: session services (in‑memory, DB, Vertex AI), event stream (user/model/tool artifacts), and state delta updates applied per event.
  - Adopt:
    - Add a simple `Session` service interface (in‑memory/SQLite) and an event model. Ensure each tool/model step can contribute a state delta (files, todos, outputs) and persist across invocations when a session is provided.

- Runner and Plugin Hooks
  - Pattern: `Runner` mediates execution with plugin callbacks (mutate user message, around execution), artifact/memory/credential services, and live vs async runs.
  - Adopt:
    - Provide a thin “runner” wrapper for DeepAgents with a basic plugin interface (on_user_message, on_event). Keep most logic in the graph; the runner adds ergonomics and integrations.

- Evaluation Framework
  - Pattern: built‑in evaluation sets, generation, LLM‑as‑judge, metrics, local/GCS result stores.
  - Adopt:
    - Leverage our Inspect integration plan for the runner; selectively incorporate ADK’s evaluator ideas (dataset schema, trajectory/response scoring patterns, LLM‑as‑judge wrappers) for parity where useful.

- Telemetry / Tracing
  - Pattern: spans for agent turns, tool calls, data send/receive; error attachment; streaming events.
  - Adopt:
    - Extend our event emission to include ADK‑style span annotations (agent name, tools, handoffs, output type), and attach errors consistently; add privacy toggles.

## Prioritized Integration Plan

Quick wins (1–3 days)
- Hooks: `before_model`, `after_model`, `before_tool`, `after_tool` with simple signatures; wire to trace events.
- Output control: support `output_schema` stop condition and `output_key` → state.
- Flow mode: `single` vs `auto` option to simplify loops during prototyping.
- Context control: `include_history` flag + `before_model_call` filter for token budget/“fresh context” runs.
- Sessions/events: minimal in‑memory session + event objects; persist state deltas per step.

Near term (1–2 weeks)
- Transfer tool: add `transfer_to_agent` handoff (in addition to current quarantine task) with peer/parent controls.
- OpenAPI toolset: parse a spec into callable tools (happy‑path subset first).
- Code executor: local sandbox tool with approvals; basic stdout/stderr capture.
- Runner wrapper: plugin hooks (on_user_message, on_event) and service slots (artifact/memory/credentials), keeping core logic in LangGraph.
- Tracing: structured spans for agents/tools with error data and privacy switches.

Later (as needed)
- Planner interface: adapter that maps “thinking_config” and produces TODO updates.
- Session backends: DB‑backed store; artifact service.
- LLM‑as‑judge utilities: integrate with Inspect’s scoring or offer a bridge.
- Live/bidi runs and resumption handles.

## Suggested API Surfaces (sketch)

- Agent creation:
  - `create_deep_agent(..., output_schema=MyModel, output_key="answer", flow_mode="single", include_history=True, input_guardrails=[...], output_guardrails=[...])`
- Hooks:
  - `before_model(state, llm_request) -> Optional[final_response]`
  - `after_model(state, llm_response) -> Optional[final_response]`
  - `before_tool(tool, args, ctx) -> Optional[result]`
  - `after_tool(tool, args, ctx, result) -> Optional[result]`
- Sessions/events:
  - `invoke(..., session=InMemorySession("user-123","sess-1"))` emits `Event`s with `state_delta` applied.
- Tools:
  - `from deepagents.tools import function_tool`
  - `from deepagents.tools.openapi import build_tools_from_openapi(spec)`
- Transfer:
  - `from deepagents.handoff import transfer_to_agent`

## Caveats
- Output schema mode must disable tool use to avoid ambiguous outcomes; document clearly.
- Flow modes and transfer flags should be obvious and consistent with sub‑agent quarantine vs handoff semantics.
- OpenAPI toolgen: start with a constrained subset; surface validation errors clearly.
- Code execution is high‑risk; require approvals and sandboxing.

## Why This Accelerates Prototyping
- Crisper loops: early stop on structured outputs; simple flow modes.
- Faster composition: transfer tool + sub‑agent patterns + function/OpenAPI tools.
- Safer experimentation: hooks and guardrails; sessionized state and events; trace visibility.
- Extensible: runner plugins and services without overhauling the graph.

## Next Steps
- Implement core hooks + output_schema/output_key + flow_mode + include_history.
- Add in‑memory Session/Event plumbing and expose to `.invoke`.
- Prototype `transfer_to_agent` and OpenAPI tool generation (narrow scope).


# ADR 0005 — Tool Parallelism and Handoff Exclusivity

Status: Proposed (tests in place; implementation pending)

Date: 2025-09-03

## Context

Inspect executes multiple tool calls emitted in a single assistant turn. Most tools are parallel‑safe; however, agent handoffs (created via `handoff(...)`) are inherently serial and change the conversation flow. Today, `agent_handoff(...)` already trims other tool calls from the sub‑agent’s conversation (“we won’t be handling the other calls”), but the top‑level `execute_tools(...)` still processes every tool call in the message one by one, so a non‑handoff tool may also run in the same turn.

References:
- `agent_handoff(...)` trims other tool calls before running the sub‑agent 〖F:external/inspect_ai/src/inspect_ai/model/_call_tools.py†L425-L436〗.
- Handoff tools are flagged as non‑parallel via metadata 〖F:external/inspect_ai/src/inspect_ai/agent/_handoff.py†L67-L72〗.
- Current execution iterates calls and creates a per‑call TaskGroup, which does not provide exclusivity 〖F:external/inspect_ai/src/inspect_ai/model/_call_tools.py†L274-L283〗.

## Decision

1) Handoff is exclusive for the turn.
- If any handoff tool appears in `tool_calls` for a message, resolve exactly one (the first by `tool_calls` order) and skip all other calls in that turn.
- Do not start non‑handoff calls in that turn.

2) Conversation vs Transcript behavior.
- Conversation: do not append messages for skipped calls (keep the sub‑agent’s context clean).
- Transcript: emit ToolEvents for each skipped call with `error.code = "skipped"` and `error.message = "Skipped due to handoff"`; include `selected_handoff_id` for attribution.

3) Multiple handoffs in the same turn.
- First handoff in `tool_calls` order wins. Others are skipped with transcript warnings and metrics (e.g., `handoff_multi_select`).

4) Parallelism for non‑handoff tools.
- Preserve/enable parallel execution for tools with `ToolDef.parallel == True`. Document that result ordering is not guaranteed; clients should join results by `tool_call_id`.
- Provide a global kill‑switch `INSPECT_DISABLE_TOOL_PARALLEL=1` (default off) to force serial execution for ops/debug.

## Rationale

- Safety and clarity: a handoff changes control flow and should not interleave with unrelated tools. Keeping the conversation free of “skipped” noise aligns with our filtering and quarantine defaults, which favor clean model contexts and environment‑driven controls 〖F:src/inspect_agents/filters.py†L200-L214〗.
- Observability: this repo emphasizes minimal, structured logs and redaction for tools 〖F:src/inspect_agents/tools.py†L61-L84〗 and transcript export with redaction 〖F:src/inspect_agents/logging.py†L1-L32〗. Recording “skipped” in the transcript (not the conversation) matches that pattern.
- Environment-driven controls: standard tools are toggled via env flags 〖F:src/inspect_agents/tools.py†L117-L162〗; a global parallelism flag is consistent with this design.

## Alternatives Considered

- Conversation-visible “skipped” ChatMessageTool: rejected to avoid confusing downstream agents and polluting context.
- Erroring on multiple handoffs: rejected to keep robustness; many models may over‑emit during exploration.
- Cancelling already-started tasks: unnecessary if we pre‑scan and avoid starting non‑handoff calls.

## Implementation Notes

- Pre‑scan `assistant.tool_calls` in `execute_tools(...)`. If any handoff is present, select the first handoff’s call id. Do not enqueue TaskGroup tasks for other tool calls.
- For each skipped call, create a ToolEvent with `pending=False` and `error={code:"skipped", message:"Skipped due to handoff"}`. Do not append a `ChatMessageTool` to the conversation.
- Maintain existing `agent_handoff(...)` conversation trimming; the pre‑scan guarantees exclusivity at the executor level.
- Respect `INSPECT_DISABLE_TOOL_PARALLEL=1` to run non‑handoff calls serially even when `ToolDef.parallel` is True.

## Testing Plan

- Parallel-safe baseline: two simple tools in one turn → both `ChatMessageTool` results present; order not asserted.
- Handoff exclusivity: one handoff + one echo tool → only a handoff outcome is added; echo is marked “skipped” in transcript; no extra conversation messages.
- Multiple handoffs: first wins; others skipped with transcript warnings and a counter increment.
- Global kill‑switch: with `INSPECT_DISABLE_TOOL_PARALLEL=1`, two parallel‑safe tools still both execute, but serially; behavior remains correct.

## Consequences

- Cleaner agent boundaries and fewer surprise side effects mid‑handoff.
- Richer transcript for debugging without leaking coordination artifacts into the model’s context.
- Predictable tie‑break (first handoff wins) and operational backstop via env flag.


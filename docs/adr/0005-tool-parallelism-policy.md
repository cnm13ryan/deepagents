# ADR 0005 — Tool Parallelism and Handoff Exclusivity

Status: Accepted — v1 (approval‑policy enforcement shipped); v2 scoped (optional executor pre‑scan)

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

This ADR is delivered in two phases to balance transcript visibility and executor‑level guarantees:

- v1 — Approval policy enforcement (current): enforce first‑handoff exclusivity via an approval policy that approves only the first handoff call and rejects all other tool calls from the same assistant turn with explanation "Skipped due to handoff exclusivity". Also emit a local tool event (`name: handoff_exclusive`, `phase: skipped`) for observability. See `handoff_exclusive_policy()` in `src/inspect_agents/approval.py`.  
  Rationale: centralizes the rule in the approval layer; keeps policy decisions visible in transcripts without changing the executor.  
  References: `handoff_exclusive_policy` 〖F:src/inspect_agents/approval.py†L195-L284〗.

- v2 — Optional executor pre‑scan (future): pre‑scan `assistant.tool_calls` in the executor (e.g., `execute_tools(...)`) and, if any handoff is present, select the first by order and avoid enqueuing all other calls from that turn. For each skipped call, mint a transcript ToolEvent with `pending=false` and `error={code:"skipped", message:"Skipped due to handoff"}` without appending any `ChatMessageTool` to the conversation. Ship behind an opt‑in flag (e.g., `INSPECT_EXECUTOR_PRESCAN_HANDOFF=1`) so v1 remains the default behavior.  
  Rationale: provides stronger executor‑level guarantees and reduces scheduling overhead while preserving transcript signals.

- Respect `INSPECT_DISABLE_TOOL_PARALLEL=1` to run non‑handoff calls serially even when `ToolDef.parallel` is True.

### Trade‑offs: Policy Visibility vs Executor Guarantees

- Policy‑first (v1):
  - Pros: explicit per‑call decisions in transcripts; minimal code surface change; resilient across executor refactors; easy to test and audit.  
  - Cons: executor still iterates over all calls (minor overhead); exclusivity depends on timely policy checks per call (though tools never execute when rejected).

- Executor pre‑scan (v2):
  - Pros: avoids enqueuing non‑selected calls entirely; stronger exclusivity guarantee at the scheduling boundary; lower overhead under high tool‑fan‑out.  
  - Cons: fewer "policy" artifacts unless we also mint explicit skip events; tighter coupling to executor internals and order semantics.

Recommendation: ship and keep v1 as the default (already implemented); offer v2 as an opt‑in for deployments that prioritize strict executor‑level gating or need to reduce scheduling overhead.

## Testing Plan

- Parallel-safe baseline: two simple tools in one turn → both `ChatMessageTool` results present; order not asserted.
- Handoff exclusivity: one handoff + one echo tool → only a handoff outcome is added; echo is marked “skipped” in transcript; no extra conversation messages.
- Multiple handoffs: first wins; others skipped with transcript warnings and a counter increment.
- Global kill‑switch: with `INSPECT_DISABLE_TOOL_PARALLEL=1`, two parallel‑safe tools still both execute, but serially; behavior remains correct.

## Consequences

- Cleaner agent boundaries and fewer surprise side effects mid‑handoff.
- Richer transcript for debugging without leaking coordination artifacts into the model’s context.
- Predictable tie‑break (first handoff wins) and operational backstop via env flag.

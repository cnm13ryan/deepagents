# TODO — Handoff Exclusivity (Turn‑Level Gating)

Status: Planned • Owner: TBA • Priority: High

## Context & Motivation
- Purpose: Ensure that when a handoff tool is present in an assistant turn, it is exclusive — only that handoff executes; all other tool calls in the same turn are not run.
- Problem: The current executor processes each tool call in sequence and can execute a non‑handoff tool alongside a handoff, contrary to design intent and agent boundary hygiene.
- User impact: Predictable control flow and cleaner sub‑agent contexts; fewer surprising side‑effects during delegation.
- Constraints: Do not add conversation‑visible artifacts for skipped calls; observability is handled via transcript events (see separate TODO).

## Implementation Guidance
- Primary file to edit:
  - `external/inspect_ai/src/inspect_ai/model/_call_tools.py` — function `execute_tools(...)`.
- Supporting code to review:
  - `external/inspect_ai/src/inspect_ai/agent/_handoff.py` — `handoff(...)` sets `TOOL_PARALLEL=False` and defines `AgentTool`.
  - `external/inspect_ai/src/inspect_ai/model/_call_tools.py` — `agent_handoff(...)` already trims other tool_calls from the sub‑agent’s conversation.
- Greppable anchors:
  - `async def execute_tools(`, `async def agent_handoff(`, `ToolEvent(`, `ToolCallError(`
- Approach sketch:
  1) Pre‑scan the last `ChatMessageAssistant` tool_calls and resolve available `ToolDef`s (via `tool_defs(tools)`).
  2) Identify handoff calls by mapping `call.function -> ToolDef` and checking if `tool_def.tool` is an `AgentTool` (or otherwise flagged non‑parallel and is a handoff).
  3) If any handoff exists, select the first by emitted order as the winner. Only enqueue that call; skip enqueuing the others (see transcript behavior in the “skipped events” TODO).
  4) Leave behavior unchanged for turns with no handoff present.

## Scope Definition
- In scope:
  - Pre‑scan and exclusive selection of a single handoff call per turn.
  - Prevent starting non‑winning calls when a handoff is present.
- Out of scope:
  - Changing `agent_handoff(...)` logic (it should remain as is).
  - Emitting conversation-visible markers for skipped calls (handled by transcript events separately).
  - Provider/model API changes.
- Likely files to modify: `_call_tools.py` only.

## Success Criteria
- Behavior: With `transfer_to_X` and a normal tool in the same turn, only the handoff yields conversation messages; the normal tool is not executed.
- Determinism: With multiple handoffs, the first in `tool_calls` order wins; others are not executed.
- Tests: Integration tests covering the above pass without xfail (see test TODO). Two parallel‑safe tools with no handoff still both execute.
- Compatibility: No changes to conversation shape except the absence of formerly concurrent non‑handoff messages.

---

### Checklist
- [ ] Pre‑scan tool_calls in `execute_tools(...)` to detect handoff presence.
- [ ] Map `function -> ToolDef` and detect handoff (AgentTool) calls.
- [ ] Execute only the first handoff; do not enqueue other calls in that turn.
- [ ] Keep non‑handoff turns behavior unchanged.
- [ ] Update/enable tests that assert exclusivity.


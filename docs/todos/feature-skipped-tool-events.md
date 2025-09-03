# TODO — Transcript “Skipped Due To Handoff” ToolEvents (No Conversation Noise)

Status: Planned • Owner: TBA • Priority: High

## Context & Motivation
- Purpose: Provide operator/developer observability when non‑winning tool calls are not executed because a handoff was present.
- Problem: Without visibility, it’s unclear why a tool didn’t run, hindering debugging and metrics.
- User impact: Clear audit trails in transcripts/logs without polluting the model conversation.
- Constraints: Do not append any `ChatMessageTool` for skipped calls; only synthesize transcript events.

## Implementation Guidance
- Primary file: `external/inspect_ai/src/inspect_ai/model/_call_tools.py`
  - Hook into the new gating logic (see handoff exclusivity TODO) inside `execute_tools(...)`.
- Event shape & logging:
  - For each skipped call: create a `ToolEvent` with `pending=False` and `error=ToolCallError(code="skipped", message="Skipped due to handoff.")`; include `id`, `function`, `arguments`, `view`.
  - Emit a single `info` log summarizing: “Skipped N tool calls due to handoff (selected=<function>/<id>).”
- Greppable anchors: `ToolEvent(`, `ToolCallError(`, `transcript()`.
- Do not add conversation messages for skipped calls.

## Scope Definition
- In scope: Emitting “skipped” ToolEvents in transcript only; one summary log line.
- Out of scope: Any ChatMessageTool or user/system notices; provider changes.
- Files likely to modify: `_call_tools.py` only.

## Success Criteria
- Transcript contains `ToolEvent` entries with `error.code == "skipped"` for every skipped call when a handoff is present.
- Conversation contains only the handoff‑related messages; no artifacts from skipped calls.
- Integration test asserts transcript presence (see tests TODO).

---

### Checklist
- [ ] In `execute_tools(...)`, when handoff gating is active, synthesize a `ToolEvent` with `error.code="skipped"` for each non‑winning call.
- [ ] Emit one summary log line for the turn.
- [ ] Ensure no `ChatMessageTool` is appended for skipped calls.
- [ ] Add tests asserting transcript “skipped” events.


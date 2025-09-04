# TODO: Transcripts — Standardized “Skipped Due to Handoff” ToolEvent

## Context & Motivation
- Purpose: ensure both v1 (policy) and future v2 (executor pre‑scan) produce a consistent transcript artifact when non‑selected tool calls are skipped.
- Problem: v1 logs only a repo‑local event; transcripts lack a standardized ToolEvent for skips.
- Value: debuggability; parity across enforcement layers.

## Implementation Guidance
- Examine: `src/inspect_agents/approval.py` (inside `handoff_exclusive_policy()`), Inspect transcript API (`inspect_ai.log._transcript`), unit tests.
- Grep tokens: `_log_tool_event(name="handoff_exclusive", phase="skipped"`, `Approval(decision="reject"`.
- Proposed event shape:
  - `type: tool_event`, `pending: false`
  - `error.code: "skipped"`, `error.message: "Skipped due to handoff"`
  - `meta.selected_handoff_id`, `meta.skipped_function`, `meta.source: "policy/handoff_exclusive"`.

## Scope Definition
- Implement: emit the ToolEvent to the transcript before returning the reject Approval; wrap in try/except so policy can't fail on logging.
- Tests: conversation with two handoffs under exclusivity -> transcript contains N "skipped" ToolEvents with the agreed fields.

## Success Criteria
- Behavior: transcript includes standardized skip artifacts; local log remains.
- Tests: green with offline unit tests.

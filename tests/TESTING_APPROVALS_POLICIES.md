# Testing Guide — Approvals & Policies

Covers Inspect-AI approvals (policies) and repo policies: handoff exclusivity and parallel kill-switch.

## What to test
- Policy decisions: approve, modify, reject, terminate for specific tools/patterns.
- Exclusivity: only the first handoff executes; others are skipped and logged.
- Parallel kill-switch: only the first non-handoff executes when enabled; others are skipped and logged.
- Presets: `ci` approves; `dev` escalates then rejects sensitive tools; `prod` terminates sensitive with redacted args.

## Patterns
- Use a lightweight apply shim when running in isolation to avoid heavy upstream deps (see tests for minimal shims).
- For end-to-end tool execution, construct a synthetic assistant message with `tool_calls` and run `execute_tools(...)`.
- Verify transcript `ToolEvent` metadata for skipped calls to ensure operator-facing signals.

## Environment toggles
- Enable parallel kill-switch with `INSPECT_TOOL_PARALLELISM_DISABLE=1` (or legacy `INSPECT_DISABLE_TOOL_PARALLEL=1`).

## Redaction
- Use `approval_preset("prod")` to assert redacted payloads contain `[REDACTED]` and do not leak raw secrets.

## Examples
- Handoff exclusivity approval (policy-only) similar to end‑to‑end tests:
  ```python
  import asyncio
  from inspect_ai.approval._policy import policy_approver
  from inspect_ai.model._chat_message import ChatMessageAssistant
  from inspect_ai.tool._tool_call import ToolCall
  from inspect_agents.approval import handoff_exclusive_policy

  def test_handoff_first_only():
      policies = handoff_exclusive_policy()
      approver = policy_approver(policies)

      calls = [
          ToolCall(id="1", function="transfer_to_reader", arguments={}),
          ToolCall(id="2", function="echo_b", arguments={}),
      ]
      msg = ChatMessageAssistant(content="", tool_calls=calls)

      ok1 = asyncio.run(approver(msg, calls[0], None, [msg]))
      ok2 = asyncio.run(approver(msg, calls[1], None, [msg]))

      assert getattr(ok1, "decision", None) == "approve"
      assert getattr(ok2, "decision", None) == "reject"
  ```

## References
- Approvals/policy usage (pytest integration is standard).

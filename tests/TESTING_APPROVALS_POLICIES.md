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

## References
- Approvals/policy usage (pytest integration is standard).

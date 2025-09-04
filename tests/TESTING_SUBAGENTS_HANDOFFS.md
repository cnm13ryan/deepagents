# Testing Guide — Subagents & Handoffs

Focus: input/output filtering, boundaries, and content shaping for subagents.

## What to verify
- Input filtering: subagent input excludes tool/system messages and is tightly bounded.
- Output filtering: supervisor receives content-only assistant messages (no tool_calls/system).
- Boundary message: first appended message is a `ChatMessageTool` describing the transfer.
- Prefixing: assistant text is prefixed with `[<agent>]`.
- Completion nudge: trailing user message indicates the subagent finished.

## Patterns
- Build handoff tool via `handoff(agent, description=..., input_filter=..., output_filter=..., tool_name=...)`.
- Use default filters from `inspect_agents.filters` unless a test needs explicit scope.
- Use `store()` to record observations from the subagent for assertions in the supervisor context.

## Tips
- Keep offline and fast; avoid real models by using trivial @agent bodies that synthesize messages.
- Scope any env overrides (`INSPECT_QUARANTINE_MODE`, etc.) with `monkeypatch` per test.

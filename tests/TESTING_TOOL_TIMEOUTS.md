# Testing Guide — Tool Timeouts

Test timeout handling and graceful fallbacks for tools.

## What to test
- Tool raises timeout error surfaces in tool message and transcript.
- Sandbox editor calls respect `INSPECT_AGENTS_TOOL_TIMEOUT` and fall back to store when editor is slow/unavailable.

## Patterns
- Build a slow tool using `anyio.move_on_after` with a small timeout and assert `TimeoutError` path.
- Stub `text_editor` to sleep longer than the configured timeout, set sandbox env (`INSPECT_AGENTS_FS_MODE=sandbox`), and assert fallback/exception semantics.
- Restore env in `finally` or via `monkeypatch` to avoid leakage.

## Env knobs
- `INSPECT_AGENTS_TOOL_TIMEOUT`: seconds per tool call in this repo’s tools.
- `INSPECT_AGENTS_FS_MODE`: `store|sandbox` mode switch.

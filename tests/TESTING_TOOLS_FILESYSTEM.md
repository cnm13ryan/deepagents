# Testing Guide — Tools & Filesystem

Covers the repo’s file tools (read/write/edit/ls/delete) in store vs sandbox modes.

## Modes
- Store (default): in-memory `Files` store, isolated per context.
- Sandbox: routes through Inspect `text_editor`/`bash_session`; delete is disabled by design.

## Security & Safety
- Deny symlinks in sandbox mode and confine to `INSPECT_AGENTS_FS_ROOT`. Validate paths before editor calls.
- Enforce per-op timeouts via `INSPECT_AGENTS_TOOL_TIMEOUT` (default ~15s).
- Enforce byte ceilings via `INSPECT_AGENTS_FS_MAX_BYTES`; raise size errors preflight (wc) or on content size.

## Typed vs string results
- Typed result models can be enabled with `INSPECT_AGENTS_TYPED_RESULTS` for richer assertions.

## Patterns
- For sandbox tests without Docker, stub `inspect_ai.tool._tools._text_editor` (and optionally `_bash_session`); the code treats stubs as sandbox-available.
- Validate delete behavior: sandbox returns `SandboxUnsupported` (or `SandboxReadOnly` if read-only flag set).
- Assert numbered line formatting from `read` (cat -n style) and truncation semantics at large line/char counts.

## Timeouts
- Simulate slow editors and assert fallback to store mode or errors as appropriate (see tool timeouts tests).

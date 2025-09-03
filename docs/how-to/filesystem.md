# Filesystem Tools — Store vs Sandbox

This page explains how DeepAgents’ file tools operate in the default in‑memory store and in optional sandbox mode, including routing, fallbacks, delete policy, and size/truncation behavior.

## Modes
- Default: `store` (in‑memory virtual filesystem; isolated per run).
- Optional: `sandbox` (routes file ops through Inspect’s sandbox tools — `text_editor`, `bash_session`).

Set via environment:
```bash
export INSPECT_AGENTS_FS_MODE=store   # default
# or
export INSPECT_AGENTS_FS_MODE=sandbox
```

## Routing
Operations are routed per mode as follows:

```mermaid
flowchart LR
  subgraph FS Tools
    L[ls] -->|store| VFS
    R[read_file] -->|store| VFS
    W[write_file] -->|store| VFS
    E[edit_file] -->|store| VFS
    D[delete_file] -->|store| VFS

    L -->|sandbox| BASH[bash_session('run','ls -1')]
    R -->|sandbox| EDIT1[text_editor('view')]
    W -->|sandbox| EDIT2[text_editor('create')]
    E -->|sandbox| EDIT3[text_editor('str_replace')]
    D -.->|sandbox| X[not supported]
  end
  VFS[(In‑memory Store)]
```

Notes
- In store mode, `ls` lists filenames from the in‑memory `Files` store (not the host filesystem).
- `ls` uses `bash_session('run', 'ls -1')` in sandbox mode.
- `read_file` uses `text_editor('view', path, view_range=[start,end])` in sandbox mode.
- `write_file` uses `text_editor('create', path, file_text=...)` in sandbox mode.
- `edit_file` uses `text_editor('str_replace', ...)` in sandbox mode.

## Fallbacks & Preflight
When sandbox mode is enabled, the tools run a quick preflight against Inspect’s sandbox service. If the sandbox is unavailable, calls gracefully fall back to the in‑memory store (no host FS writes). A warning is logged once.

## Delete Policy
- `delete_file` is supported only in `store` mode.
- In `sandbox` mode, delete is intentionally disabled and returns a structured error indicating it’s unsupported. The message includes guidance to switch to store mode.

## Confinement, Symlinks, and Size
- Root confinement (sandbox): file paths are validated to live under `INSPECT_AGENTS_FS_ROOT` (absolute, default `/repo`). Attempts to access paths outside the root are rejected before invoking the editor.
- Symlink denial (sandbox): symbolic links are denied for read/write/edit as a safety measure.
- Store mode safety: the store is in‑memory and never touches host FS, so path escape and symlink concerns do not apply.
- Size ceiling (both modes): `INSPECT_AGENTS_FS_MAX_BYTES` caps bytes for read/write/edit. Default 5,000,000 bytes. Exceeding the cap raises `FileSizeExceeded` with actual/max sizes.

### Quick Examples
```bash
# Enforce a 512 KiB ceiling across both modes
export INSPECT_AGENTS_FS_MAX_BYTES=$((512*1024))

# Sandbox confinement under /repo (absolute path)
export INSPECT_AGENTS_FS_MODE=sandbox
export INSPECT_AGENTS_FS_ROOT=/repo
```

```json
// Read in sandbox: path outside root is rejected
{"params": {"command": "read", "file_path": "/etc/hosts"}}
```

```bash
# Symlink denial (sandbox): operations targeting a symlink are denied
ln -sf /secret /repo/link
```

## Timeouts & Size/Truncation
- Per‑call timeout: 15 seconds by default; override with `INSPECT_AGENTS_TOOL_TIMEOUT=<seconds>`.
- `read_file` caps each returned line to 2000 characters before numbering. Empty files return a friendly “empty contents” message.
- Tool event logs truncate long string fields (default 200 chars) for observability; configure with `INSPECT_TOOL_OBS_TRUNCATE`.
- Inspect also applies a global tool‑output truncation envelope (16 KiB default) outside of these file‑specific limits (see decision doc).

## Typed Results (optional)
Set `INSPECT_AGENTS_TYPED_RESULTS=1` to receive structured results:
- `ls` → `{ files: list[string] }`
- `read_file` → `{ lines: list[string], summary: string }`
- `write_file` → `{ path: string, summary: string }`
- `edit_file` → `{ path: string, replaced: int, summary: string }`

## Examples
```bash
# Sandbox mode with timeouts and typed results
export INSPECT_AGENTS_FS_MODE=sandbox
export INSPECT_AGENTS_TOOL_TIMEOUT=20
export INSPECT_AGENTS_TYPED_RESULTS=1
```

## See Also
- Reference: ../reference/environment.md
- Tool pages: ../tools/ls.md, ../tools/read_file.md, ../tools/write_file.md, ../tools/edit_file.md
- ADR: ../adr/0004-filesystem-sandbox-guardrails.md
- Truncation decision: ../adr/0004-tool-output-truncation.md

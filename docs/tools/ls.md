---
title: "ls Reference"
status: draft
kind: builtin
mode: stateless
owner: docs
---

# ls

## Overview
- Lists filenames from the virtual in‑memory `Files` store. In sandbox mode, proxies to a shell `ls -1` in an isolated environment.
- Use to discover files before read/edit operations.
- Classification: stateless.

## Parameters
- instance: string — Optional `Files` instance name for isolation.

## Result Schema
- Default: list[string] — Filenames.
- Typed (when `INSPECT_AGENTS_TYPED_RESULTS=1`): `{ files: list[string] }` (`FileListResult`).

## Timeouts & Limits
- Execution timeout: 15s; no explicit result cap.

## Sandbox Notes
- When `INSPECT_AGENTS_FS_MODE=sandbox` and sandbox is available, `ls` routes to `bash_session('run', 'ls -1')`. If the sandbox is unavailable, it falls back to the in‑memory store.
- Delete operations are not available via `ls`; `delete_file` is a separate tool and is disabled in sandbox mode.

## Examples
### Typed vs Legacy (quick look)

Args
```json
{}
```

Typed
```json
{ "files": ["README.md", "src/", "docs/"] }
```

Legacy
```json
["README.md", "src/", "docs/"]
```

See also: [Typed Results vs Legacy Outputs](typed_results.md).

## Troubleshooting
- Empty list — Ensure files exist in the chosen `instance` or that you’re operating in the expected execution context.

## Source of Truth
- Code: src/inspect_agents/tools_files.py (execute_ls), src/inspect_agents/tools.py (ls wrapper)
- Guides: ../guides/tool-umbrellas.md
- See also: [files](files.md) (unified files tool)

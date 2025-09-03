---
title: "Tool Defaults"
status: draft
owner: docs
updated: 2025-09-03
---

# Tool Defaults (Authoritative)

Central source for shared limits, environment flags, and behaviors used by built‑in tools. Individual tool pages should reference this to avoid drift.

## Core Environment Flags
- INSPECT_AGENTS_TOOL_TIMEOUT: Default execution timeout (seconds). Code default is 15.0s. Used across file tools and wrappers. Example implementation reads from env and falls back to 15.  
  Source: tools_files `_default_tool_timeout()` and tools `_default_tool_timeout()`.
- INSPECT_AGENTS_FS_MODE: Filesystem routing; `store` (default) uses an in‑memory store, `sandbox` proxies to Inspect’s editor/shell helpers when available.  
  Source: tools_files `_use_sandbox_fs()`.
- INSPECT_AGENTS_TYPED_RESULTS: When truthy (1/true/yes/on), tools return typed Pydantic models instead of strings/lists.  
  Source: tools_files `_use_typed_results()`.
- INSPECT_TOOL_OBS_TRUNCATE: Max characters for string fields in tool‑arg logging (observability). Default 200 chars; overage appended as `...[+N chars]`.  
  Source: tools `_OBS_TRUNCATE` and `_redact_and_truncate()`.

## File Tools — Defaults & Limits
These apply to the unified `files` tool and its backward‑compatible wrappers (`read_file`, `write_file`, `edit_file`, `ls`, `delete_file`).

- read_file
  - Timeout: 15s (see global).  
  - Line window: default `offset=0`, `limit=2000` lines.  
  - Per‑line truncation: 2000 characters before numbering; output is left‑padded line numbers + tab.  
  - Empty file message: “System reminder: File exists but has empty contents”.
- write_file
  - Timeout: 15s.  
  - Size caps: no explicit size limit in store mode; sandbox editor may impose provider limits.  
  - Content is written as provided (no newline normalization).
- edit_file
  - Timeout: 15s.  
  - Semantics: string replace; first occurrence by default, or all when `replace_all=true`.  
  - Replacement count is exact in store mode; sandbox mode may report an approximate value.
- ls
  - Timeout: 15s.  
  - No explicit result count cap; sandbox mode proxies to `ls -1`.
- delete_file
  - Timeout: 15s.  
  - Disabled in sandbox mode; store mode only (idempotent when file absent).

## Todos Tools — Defaults & Limits
- write_todos
  - Timeout: 15s.  
  - No explicit list length cap; tool‑arg logging truncates long strings to `INSPECT_TOOL_OBS_TRUNCATE` (default 200 chars).
- update_todo_status
  - Timeout: 15s.  
  - Validated transitions with optional `allow_direct_complete`.

## Provider/Session‑Backed Tools (Notes)
- bash / python: Document the 15s default and that a per‑call `timeout` parameter (when exposed) may override. Output truncation is subject to caller usage and logs still truncate args via `INSPECT_TOOL_OBS_TRUNCATE`.
- web_search: Use the 15s agent‑side guard; provider quotas and their own HTTP timeouts also apply.
- web_browser_*: Navigation and interaction timeouts depend on the underlying browser/runtime in addition to the 15s guard; note session lifetime/parallelism are provider‑dependent.

## Documentation Guidance
- In each tool page’s “Timeouts & Limits”, include: “Execution timeout: 15s (INSPECT_AGENTS_TOOL_TIMEOUT). See Tool Defaults for shared caps and provider notes.”
- Only add per‑tool exceptions where behavior meaningfully differs (e.g., provider/session limits or per‑call overrides).


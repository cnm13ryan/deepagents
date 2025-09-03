# Canonical and Standard Tools — Stateless vs Stateful Umbrellas

This page maps the tools exposed by the Inspect‑AI path in this repo into two umbrellas, following the definitions and guidance in `./stateless-vs-stateful-tools-harmonized.md`:

- Stateless: no retained in‑memory/process state between calls; each invocation is self‑contained.
- Stateful: maintains per‑session state (e.g., long‑lived processes or browser contexts) addressed by a session id.

Refer to `./stateless-vs-stateful-tools-harmonized.md` for full design/ops guidance.

## Stateless Umbrella

Canonical (built‑in) tools:

- `write_todos` — write the complete todo list to the shared `Todos` StoreModel.
- `update_todo_status` — validated status transitions for a single todo; returns JSON payload.
- `ls` — list filenames in the virtual in‑memory `Files` store (optionally namespaced via `instance`).
- `read_file` — return numbered lines from a file with truncation and bounds checks.
- `write_file` — write file content; bounded timeout.
- `edit_file` — single‑string replace (first or all occurrences) then write back.

Notes:
- These operate entirely via parameters and StoreModel lookups; they do not require or create a session identifier. In sandbox FS mode they route to `text_editor(...)` for the actual edit/read, which is still used per‑call without a session handle.

Standard tools:

- `think` — appends a thought to the log; no side effects.
- `web_search` — one‑shot web queries via a configured provider; no session retained.
- `bash` — executes a single bash command in a sandboxed process; no session continuity.
- `python` — executes a single Python script in a sandboxed process; no session continuity.
- `text_editor` — in‑process JSON‑RPC tool for `view`, `create`, `str_replace`, `insert`, `undo_edit`; commands are parameterized and per‑call.

## Stateful Umbrella

Standard tools:

- `web_browser_*` — navigation and interaction tools backed by a persistent browser/context. A per‑session id is created on first use and attached to subsequent calls. Multiple tool names (e.g., `web_browser_go`, `web_browser_click`, `web_browser_type_submit`, `web_browser_scroll`, `web_browser_back`, `web_browser_forward`, `web_browser_refresh`) share the same session.
- `bash_session` — interactive shell session with actions (`type`, `type_submit`, `read`, `interrupt`, `restart`) bound to a long‑lived shell process identified by a session id. Not enabled by default in this repo’s helper (`standard_tools()`), but part of Inspect’s standard toolset.

## FS Mode and Safety

- By default, file tools (`ls`, `read_file`, `write_file`, `edit_file`) use the in‑memory `Files` StoreModel (stateless per call). When `INSPECT_AGENTS_FS_MODE=sandbox`, these tools proxy to `text_editor(...)` against a host‑mounted sandbox. This does not introduce per‑session browser/shell state; treat them as stateless for categorization here.

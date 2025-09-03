# Tools Reference

This section provides per-tool reference pages for all built-in and standard tools exposed by Inspect Agents.

- What each tool does and when to use it.
- Stateless vs stateful classification and lifecycle notes.
- Parameters and result schema.
- Copy-paste examples and common troubleshooting guidance.

Tools are grouped as follows:

## Built-in (Inspect Agents)

- [write_todos](write_todos.md)
- [update_todo_status](update_todo_status.md)
- [ls](ls.md)
- [read_file](read_file.md)
- [write_file](write_file.md)
- [edit_file](edit_file.md)
 - [delete_file](delete_file.md)
 - [files](files.md) — unified file operations (ls/read/write/edit/delete)
- [delete_file](delete_file.md)
- [files](files.md)

## Standard (Optional Providers)

- [think](think.md)
- [web_search](web_search.md)
- [bash](bash.md)
- [python](python.md)
- [text_editor](text_editor.md)
- [web_browser](web_browser.md)

See also: ../guides/tool-umbrellas.md and ../guides/stateless-vs-stateful-tools-harmonized.md.

## Return Types Summary

Many tools support two return styles controlled by the `INSPECT_AGENTS_TYPED_RESULTS` env var.

- Default returns are strings or lists for brevity.
- Typed returns are Pydantic models with stable fields useful for programmatic handling.

Tool | Default Return | Typed Model | Key Fields
---- | -------------- | ----------- | ---------
[read_file](read_file.md) | string (numbered lines) | `FileReadResult` | `lines: list[str]`, `summary: str`
[write_file](write_file.md) | string (summary) | `FileWriteResult` | `path: str`, `summary: str`
[edit_file](edit_file.md) | string (summary) | `FileEditResult` | `path: str`, `replaced: int`, `summary: str`
[ls](ls.md) | list[string] | `FileListResult` | `files: list[str]`
[write_todos](write_todos.md) | string (summary) | `TodoWriteResult` | `count: int`, `summary: str`
[update_todo_status](update_todo_status.md) | string (JSON text) | `TodoStatusResult` | `index: int`, `status: str`, `warning: str | None`, `summary: str`

Notes
- File tools also operate in sandbox mode when `INSPECT_AGENTS_FS_MODE=sandbox`; behavior notes are on each page.
- For `edit_file`, replacement count may be approximate in sandbox mode.
- Filesystem: In store mode, `ls` lists filenames from the in-memory Files store (not the host filesystem). See ../how-to/filesystem.md.

See also: [Typed Results vs Legacy Outputs](typed_results.md) for canonical examples and enablement details (`INSPECT_AGENTS_TYPED_RESULTS`).

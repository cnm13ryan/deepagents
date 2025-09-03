# TODO — Sandbox/Host FS Mode (optional)

Context & Motivation
- Add an optional mode to operate on a real filesystem via Inspect’s `text_editor` tool (in sandbox), for workflows requiring actual files.

Implementation Guidance
- Read: `external/inspect_ai/src/inspect_ai/tool/_tools/_text_editor.py`  
  Grep: `def text_editor(`, commands `view/create/str_replace/insert`

- Scope — Do
- [x] Extend file tools with a feature flag to route via Inspect `text_editor` when `INSPECT_AGENTS_FS_MODE=sandbox` (implemented in `src/inspect_agents/tools_files.py` and used by wrappers in `tools.py`):
  - [x] `read_file` → `text_editor('view', path, view_range=...)`
  - [x] `write_file` → `text_editor('create', path, file_text=...)`
  - [x] `edit_file` → `text_editor('str_replace', path, old_str=..., new_str=...)`
  - [ ] `ls` → (optional) shell or tracked index
- [x] Tests `tests/unit/inspect_agents/test_fs_sandbox.py` using a stub/mocked editor; no disk writes. When sandbox is unavailable, verify graceful fallback to Store-backed mode with a clear warning.

Scope — Don’t
- Do not default to host FS; default remains Store-backed

Success Criteria
- [x] Commands assembled correctly; tests pass without external sandbox
- [ ] Security notes documented in tool docstrings

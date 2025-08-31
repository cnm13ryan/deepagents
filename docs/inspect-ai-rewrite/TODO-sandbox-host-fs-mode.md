# TODO — Sandbox/Host FS Mode (optional)

Context & Motivation
- Add an optional mode to operate on a real filesystem via Inspect’s `text_editor` tool (in sandbox), for workflows requiring actual files.

Implementation Guidance
- Read: `external/inspect_ai/src/inspect_ai/tool/_tools/_text_editor.py`  
  Grep: `def text_editor(`, commands `view/create/str_replace/insert`

Scope — Do
- [ ] Extend `src/inspect_agents/tools.py` with a feature flag (env or parameter) to route:
  - [ ] `read_file` → `text_editor('view', path, view_range=...)`
  - [ ] `write_file` → `text_editor('create', path, file_text=...)`
  - [ ] `edit_file` → `text_editor('str_replace', path, old_str=..., new_str=...)`
  - [ ] `ls` → shell or tracked index (keep simple; optional)
- [ ] Tests `tests/inspect_agents/test_fs_sandbox.py` using a stub/mocked editor; no disk writes

Scope — Don’t
- Do not default to host FS; default remains Store-backed

Success Criteria
- [ ] Commands assembled correctly; tests pass without external sandbox
- [ ] Security notes documented in tool docstrings


# DONE — Virtual FS Tools (Store-backed)

Context & Motivation
- Recreate deepagents in-memory file tools on Inspect’s Store: `ls`, `read_file`, `write_file`, `edit_file`.
- Maintain behavior (errors, cat -n formatting, uniqueness rules).

Implementation Guidance
- Read: `src/deepagents/tools.py` for parity  
  Grep: `def ls`, `def read_file`, `def write_file`, `def edit_file`, `replace_all`  
  Note cat -n output and line truncation

Scope — Do
- [x] Implement in `src/inspect_agents/tools.py`:
  - [x] `@tool() def ls() -> list[str]`
  - [x] `@tool() def read_file(path: str, offset: int = 0, limit: int = 2000) -> str`
  - [x] `@tool() def write_file(path: str, content: str) -> str`
  - [x] `@tool() def edit_file(path: str, old_string: str, new_string: str, replace_all: bool = False) -> str`
  - [x] `@tool() def delete_file(path: str) -> str` (store mode; sandbox unsupported by design)
- [x] Mirror error semantics and include stable error codes/phrases (missing file, offset > len, uniqueness advisory) without overfitting to exact strings
- [x] Tests `tests/unit/inspect_agents/test_fs_tools.py` covering:
  - [x] `ls` lists keys
  - [x] `read_file` offset/limit + cat -n formatting + 2k char truncation
  - [x] `write_file` persists content
  - [x] `edit_file` uniqueness vs `replace_all=True`
  - [x] Instance‑scoped Files model for isolation
  - [x] `delete_file` semantics (existing, idempotent, isolation) and sandbox-mode error

Scope — Don’t
- No disk IO; Store only (host FS mode is a separate feature)

Success Criteria
- [ ] All tests pass and behavior matches existing examples
- [x] No LangChain/LangGraph imports

# done — TODO — Virtual FS Tools (Store-backed)

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
- [x] Mirror error semantics and include stable error codes/phrases (missing file, offset > len, uniqueness advisory) without overfitting to exact strings
- [ ] Tests `tests/inspect_agents/test_fs_tools.py` covering:
  - [ ] `ls` lists keys
  - [ ] `read_file` offset/limit + cat -n formatting + 2k char truncation
  - [ ] `write_file` persists content
  - [ ] `edit_file` uniqueness vs `replace_all=True`
  - [ ] Optional: instance‑scoped Files model (e.g., `Files(instance='agentA')`) to prove isolation when desired

Scope — Don’t
- No disk IO; Store only (host FS mode is a separate feature)

Success Criteria
- [ ] All tests pass and behavior matches existing examples
- [x] No LangChain/LangGraph imports

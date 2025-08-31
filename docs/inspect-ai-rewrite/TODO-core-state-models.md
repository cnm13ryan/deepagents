# TODO — Core State Models (Store-backed)

Context & Motivation
- Replace custom LangGraph state (todos/files) with Inspect-AI `Store` and typed `StoreModel` to enable durable, transcripted per-sample state.
- Users get reliable persistence, easier composition, and observability of state changes.

Implementation Guidance
- Read: `src/deepagents/state.py` (fields `todos`, `files`) and reducer  
  Grep: `DeepAgentState`, `Todo`, `files:`  
- Read: `external/inspect_ai/src/inspect_ai/util/_store.py` and `_store_model.py`  
  Grep: `class Store`, `def store()`, `class StoreModel`  
  Note: `StoreModel` automatically namespaces as `ClassName[:instance]:field` — do NOT invent custom `key` attributes.

Scope — Do
- [ ] Create `src/inspect_agents/state.py` with:
  - [ ] `class Todo(BaseModel): content: str; status: Literal['pending','in_progress','completed']`
  - [ ] `class Todos(StoreModel): todos: list[Todo] = []` (namespaced as `Todos:todos`)
  - [ ] `class Files(StoreModel): files: dict[str, str] = {}` (namespaced as `Files:files`)
  - [ ] Optional isolation: use `Todos(instance='supervisor')` or per sub‑agent `instance` to avoid cross‑talk.
  - [ ] Accessors: `get_todos()/set_todos()`, `get_file()/put_file()/list_files()`
- [ ] Ensure all values are JSON-serializable (Pydantic models OK)
- [ ] Unit tests in `tests/inspect_agents/test_state.py`

Scope — Don’t
- Do not modify `external/inspect_ai/*` (submodule) or existing `src/deepagents/*`.

Success Criteria
- [ ] Tests pass for get/set/delete semantics and default initialization
- [ ] Store changes appear in transcripts: run code inside a `span(...)` or via `agent.run(...)` and assert a `StoreEvent` was recorded.
- [ ] No LangChain/LangGraph dependencies

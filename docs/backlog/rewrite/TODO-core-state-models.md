# DONE — Core State Models (Store-backed)

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
- [x] Create `src/inspect_agents/state.py` with:
  - [x] `class Todo(BaseModel): content: str; status: Literal['pending','in_progress','completed']`
  - [x] `class Todos(StoreModel): todos: list[Todo] = []` (namespaced as `Todos:todos`)
  - [x] `class Files(StoreModel): files: dict[str, str] = {}` (namespaced as `Files:files`)
  - [x] Isolation defaults: use `Files(instance=<agent_name>)` by default in agent builders; keep `Todos` shared; document how to opt into shared Files if desired.
  - [x] Accessors: `get_todos()/set_todos()`, `get_file()/put_file()/list_files()`
- [x] Ensure all values are JSON-serializable (Pydantic models OK)
- [x] Unit tests present under `tests/unit/inspect_agents` use these models

Scope — Don’t
- Do not modify `external/inspect_ai/*` (submodule) or existing `src/deepagents/*`.

Success Criteria
- [x] Tests cover get/set and update semantics (delete implemented on `Files`)
- [x] Store changes appear in transcripts (see `write_transcript()` helper in logging docs)
- [x] No LangChain/LangGraph dependencies

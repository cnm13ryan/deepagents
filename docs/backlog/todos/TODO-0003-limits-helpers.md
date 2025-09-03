# TODO 0003 — Limits Convenience Helpers (`inspect_agents.limits`)

Context & Motivation
- Purpose: Provide a tiny facade so repo users don’t import Inspect internals directly.
- Problem: Callers must know `inspect_ai.util._limit` APIs; a thin re-export improves ergonomics and buffers version drift.
- Constraint: Keep imports light; no heavy imports at module import time.

Scope
- Add `src/inspect_agents/limits.py` with typed helpers: `message(n)`, `tokens(n)`, `time(seconds)`, `working(seconds)`, and `parse_spec(spec: str)`.
- Optionally re-export from `src/inspect_agents/__init__.py`.

Files & Pointers
- New module: `src/inspect_agents/limits.py` (defer Inspect imports inside functions).
- Inspect constructors (read-only): `external/inspect_ai/src/inspect_ai/util/_limit.py`.  
  〖F:external/inspect_ai/src/inspect_ai/util/_limit.py†L237-L246〗 〖F:external/inspect_ai/src/inspect_ai/util/_limit.py†L281-L289〗 〖F:external/inspect_ai/src/inspect_ai/util/_limit.py†L318-L321〗
- Call sites that may benefit: CLI (TODO-0002), config parsing (TODO-0005).

Tasks
- [ ] Implement helpers returning Inspect `Limit` instances. Use local parsing for `parse_spec`:
  - Accept `message=<int>`, `tokens=<int|n[k|m]>`, `time=<float>s`, `working=<float>s`.
- [ ] Add minimal docstrings and type hints following repo style.
- [ ] (Optional) Update examples to import from `inspect_agents.limits`.

Acceptance Criteria
- `from inspect_agents.limits import message, tokens, time, working, parse_spec` works and returns `Limit` objects.
- Invalid specs raise `ValueError` with actionable messages.

Test Plan
- [ ] Unit tests for `parse_spec()` covering ints, floats, suffixes, invalid input.
- Command: `CI=1 NO_NETWORK=1 PYTHONPATH=src:external/inspect_ai .venv/bin/pytest -q tests/unit/inspect_agents -k limits_helpers`.

Risks & Rollback
- Risk: import cycles. Mitigation: local (in-function) imports from Inspect.
- Rollback: delete the module; callers can import Inspect directly.

---


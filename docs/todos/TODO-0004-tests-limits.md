# TODO 0004 — Deterministic Integration/Unit Tests for Limits

Context & Motivation
- Purpose: Ensure limit plumbing remains correct and stable.
- Problem: Explicit tests for message/time limits through our paths are missing.
- Constraint: Keep tests offline, deterministic, and fast.

Scope
- Add new tests verifying: handoff message limit early exit; runner time limit early exit; supervisor `attempts>1` smoke.
- Prefer message/tool-call limits for determinism; wall-time with slack only.

Files & Pointers
- Existing patterns: `tests/integration/inspect_agents/test_run.py` (toy model + run_agent).  
  〖F:tests/integration/inspect_agents/test_run.py†L11-L23〗 〖F:tests/integration/inspect_agents/test_run.py†L33-L49〗
- Handoff construction: `src/inspect_agents/agents.py` (build_subagents → handoff).  
  〖F:src/inspect_agents/agents.py†L223-L231〗
- Runner: `src/inspect_agents/run.py`.  
  〖F:src/inspect_agents/run.py†L21-L27〗

Tasks
- [ ] Add `tests/integration/inspect_agents/test_limits.py` with:
  - Handoff message limit: sub-agent that would do ≥2 turns; `handoff(..., limits=[message_limit(1)])`; assert early exit/limit reason.
  - Runner time limit: `run_agent(..., limits=[time_limit(0.2)])` with toy sleep; assert early exit.
  - Supervisor attempts>1: set `attempts=2`; toy model submits on second turn; assert ≥2 messages and completion present.
- [ ] Mark time-based test as slow if needed; avoid token-limit tests.

Acceptance Criteria
- New tests pass locally/CI; total time < 3s on dev machines.

Test Commands
- `CI=1 NO_NETWORK=1 PYTHONPATH=src:external/inspect_ai .venv/bin/pytest -q tests/integration/inspect_agents -k limits`.

Risks & Rollback
- Risk: flakiness due to time; use generous slack and simple sleeps.
- Rollback: skip time-based case; keep message-limit test.

---


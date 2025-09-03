# TODO 0001 — Structured Observability for Limits (Nearing + Exceeded)

Context & Motivation
- Purpose: Emit clear, machine-parseable logs when execution limits are nearing (≥80%) or exceeded, to aid tuning, guardrails, and incident analysis.
- Problem: Only sample-level exceeded events are visible via Inspect transcript; no early warnings or uniform JSON logs across runner vs. handoff scopes.
- Constraints: Do not fork Inspect; integrate via our run/handoff layers. Keep overhead negligible.

Scope
- Implement JSON logs for `limit_nearing` and `limit_exceeded` at the runner level; handoff-level logging is desirable but optional in v1.
- Do not change core Inspect behavior or result types; additive logging only.

Files & Pointers
- Runner entry: `src/inspect_agents/run.py` — after `agent_run(...)`, inspect limits and transcript.  
  Grep: `async def run_agent`, `limits=`. 〖F:src/inspect_agents/run.py†L21-L27〗
- Logging helpers: `src/inspect_agents/logging.py` — add `log_limit_event(kind, scope, fields)` utility (follows `_event_to_dict` style).  
  Grep: `write_transcript`, `DEFAULT_LOG_DIR`. 〖F:src/inspect_agents/logging.py†L41-L60〗
- Inspect limits API (read-only): `external/inspect_ai/src/inspect_ai/util/_limit.py` — `sample_limits()`, `Limit`, usage/limit.  
  〖F:external/inspect_ai/src/inspect_ai/util/_limit.py†L73-L116〗 〖F:external/inspect_ai/src/inspect_ai/util/_limit.py†L195-L217〗
- Transcript event shape (read-only): `external/inspect_ai/src/inspect_ai/log/_transcript.py` — `SampleLimitEvent`.  
  〖F:external/inspect_ai/src/inspect_ai/log/_transcript.py†L103-L118〗

Tasks
- [ ] Add `log_limit_event(event: str, scope: str, fields: dict)` in `logging.py` that writes one JSON line (use `logger.info`).
- [ ] In `run.py`, after `agent_run(...)` returns, compute per-kind usage vs configured limit via `sample_limits()`. If limit present and 0.8 ≤ usage/limit < 1.0, emit `limit_nearing` with fields `{limit_kind, threshold, used, remaining, agent_name}`.
- [ ] Detect exceeded via transcript events (`SampleLimitEvent`) or usage ≥ limit and emit `limit_exceeded` once per kind.
- [ ] Include scope=`runner` for these events. (Optional) For handoffs, explore callback or wrapper to log scope=`handoff` when `handoff(..., limits=[...])` triggers.
- [ ] Redact nothing (numbers only). Ensure log volume is O(1) per run.

Acceptance Criteria
- When a run hits a runner time limit, one `limit_exceeded` JSON log is emitted with fields: `event, scope, limit_kind, threshold, used`.
- When usage reaches ≥80% but below limit, one `limit_nearing` log is emitted.
- No changes to returned `AgentState`.

Test Plan
- Add `tests/integration/inspect_agents/test_limits.py` (see TODO-0004):
  - [ ] Runner time limit: `time_limit(0.2)` with toy sleep; assert `limit_exceeded` log captured.
  - [ ] Message nearing: large message cap plus synthetic usage to cross 80%; assert `limit_nearing` log.
- Run: `CI=1 NO_NETWORK=1 PYTHONPATH=src:external/inspect_ai .venv/bin/pytest -q tests/integration/inspect_agents -k limits`.

Risks & Rollback
- Risk: logging overhead. Mitigation: O(1) checks/logs.  
- Rollback: Remove calls in `run.py`; keep helper unused.

---


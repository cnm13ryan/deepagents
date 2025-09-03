# TODO 0006 — Optional "Stopped Due to Limit" Footer in Completion

Context & Motivation
- Purpose: Inform users when an answer may be incomplete due to a limit.
- Problem: Truncated/early-stop behavior can confuse users without an explicit note.
- Constraint: Off by default; opt-in via env flag.

Scope
- Append a short footer to `result.output.completion` when `INSPECT_LIMIT_FOOTER=1` and a sample limit event is present.
- Do not change agent behavior; annotate output only.

Files & Pointers
- Runner entry: `src/inspect_agents/run.py` — where `AgentState` is returned.  
  〖F:src/inspect_agents/run.py†L21-L27〗
- Transcript: `external/inspect_ai/src/inspect_ai/log/_transcript.py` — `SampleLimitEvent` fields.  
  〖F:external/inspect_ai/src/inspect_ai/log/_transcript.py†L103-L118〗
- Logging helper (optional): `src/inspect_agents/logging.py` to fetch/write transcript/artifacts.  
  〖F:src/inspect_agents/logging.py†L41-L60〗

Tasks
- [ ] Check `INSPECT_LIMIT_FOOTER` env in `run.py` after `agent_run(...)`.
- [ ] If a `sample_limit` event exists, append a footer like: `\n\nNote: Stopped due to <limit_kind>=<threshold>; answer may be incomplete.`
- [ ] If no completion is present, create a minimal completion containing only the footer.

Acceptance Criteria
- With `INSPECT_LIMIT_FOOTER=1`, limit-triggered runs include the footer; without it, no change in output.

Test Plan
- [ ] Unit test simulating a limit event (or forcing one via tiny message/time cap) and asserting footer behavior for both env on/off.
- Command: `CI=1 NO_NETWORK=1 PYTHONPATH=src:external/inspect_ai .venv/bin/pytest -q tests/integration/inspect_agents -k limit_footer`.

Risks & Rollback
- Risk: double footers on retries. Mitigation: idempotent append (check marker string).
- Rollback: remove env check and footer append code.

---


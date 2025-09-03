# TODO 0002 — CLI Flags to Apply Limits at Runtime

Context & Motivation
- Purpose: Users can set execution budgets (messages/tokens/time/working) without code changes.
- Problem: `examples/inspect/run.py` lacks `--limit` flags; limits cannot be applied from CLI.
- Constraint: Map flags to Inspect limit objects and pass to `run_agent(..., limits=...)`.

Scope
- Add repeatable `--limit` flags to `examples/inspect/run.py` that accept specs like `message=24`, `tokens=20k`, `time=90s`, `working=60s`.
- Parse to Inspect limit instances and forward into `run_agent`.
- Maintain backward compatibility for existing flags and behavior.

Files & Pointers
- CLI: `examples/inspect/run.py` — argparse setup and `run_agent(...)` call.  
  Grep: `argparse`, `--enable-`, `run_agent(`, `limits=`. 〖F:examples/inspect/run.py†L88-L101〗 〖F:examples/inspect/run.py†L149-L157〗
- Runner: `src/inspect_agents/run.py` — accepts `limits` list.  
  〖F:src/inspect_agents/run.py†L21-L27〗
- Limit constructors (read-only): `external/inspect_ai/src/inspect_ai/util/_limit.py` — `message_limit`, `token_limit`, `time_limit`, `working_limit`.  
  〖F:external/inspect_ai/src/inspect_ai/util/_limit.py†L237-L246〗 〖F:external/inspect_ai/src/inspect_ai/util/_limit.py†L281-L289〗 〖F:external/inspect_ai/src/inspect_ai/util/_limit.py†L318-L321〗
- Optional helper: `src/inspect_agents/limits.py` from TODO-0003 for parsing.

Tasks
- [ ] Extend argparse with `--limit SPEC` (action=`append`). Document in `--help`.
- [ ] Implement `parse_limit_spec(str) -> Limit` locally or import from `inspect_agents.limits` (see TODO-0003). Support:
  - `message=<int>`; `tokens=<int|n[k|m]>`; `time=<float>s`; `working=<float>s`.
- [ ] Construct list of limits from repeated flags and call `await run_agent(agent, user_input, limits=limits)`.
- [ ] Validate inputs; show helpful errors for malformed specs.

Acceptance Criteria
- Running `uv run python examples/inspect/run.py "..." --limit message=2` terminates early due to message cap (see logs/transcript), process exits 0.
- `--limit tokens=20000 --limit time=90s` accepted and forwarded (manual verification in logs/transcript).

Test Plan
- [ ] Add an integration test that invokes `_main()` programmatically with `--limit message=1` and a toy agent; assert reduced messages and completion (or limit event).
- Command: `CI=1 NO_NETWORK=1 PYTHONPATH=src:external/inspect_ai .venv/bin/pytest -q tests/integration/inspect_agents -k cli_limits`.

Risks & Rollback
- Risk: conflicting flags. Mitigation: strict parser + clear errors.
- Rollback: isolate changes to CLI file; remove flag handling.

---


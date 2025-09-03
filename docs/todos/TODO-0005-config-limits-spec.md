# TODO 0005 — Parse YAML “Limits Spec” in Config Loader

Context & Motivation
- Purpose: Enable declarative limits in YAML mapped to concrete Inspect Limit objects.
- Problem: Config treats `limits` as `list[Any]` without parsing; docs show a spec users expect to work.  
  Pointers: Root schema has `limits: list[Any]` and sub-agent configs support `limits`. 〖F:src/inspect_agents/config.py†L32-L39〗 〖F:src/inspect_agents/agents.py†L223-L231〗
- Constraint: Keep `build_from_config` return shape stable.

Scope
- Implement a parser that converts dict or string specs into Inspect `Limit` objects.
- Make it opt-in: expose `parse_limits_spec(...)` from `inspect_agents.limits` and use it in config loader where applicable.

Files & Pointers
- Config loader: `src/inspect_agents/config.py` — `load_yaml`, `build_from_config`, `load_and_build`.  
  〖F:src/inspect_agents/config.py†L53-L58〗 〖F:src/inspect_agents/config.py†L116-L128〗
- Helpers: `src/inspect_agents/limits.py` (TODO-0003) to implement `parse_limits_spec`.
- Example spec (docs): `docs/subagents.md` shows dict/string forms.  
  〖F:docs/subagents.md†L64-L72〗

Tasks
- [ ] Implement `parse_limits_spec(spec: list[dict]|list[str]) -> list[Limit]` in `inspect_agents.limits` supporting:
  - Dict: `{type: time, seconds: 60}`, `{type: messages, max: 8}`, `{type: tokens, max: 6000}`.
  - String: `time=60s`, `message=8`, `tokens=6000`.
- [ ] In `build_from_config`, if `cfg.limits` present, parse and return them alongside agent/tools/approvals (do not modify supervisor construction yet).
- [ ] For sub-agents, if a `limits` list contains spec dicts/strings, parse before calling `build_subagents` so each handoff receives `Limit` objects.
- [ ] Error handling: raise `ValueError` on unknown types/fields with actionable message.

Acceptance Criteria
- `load_and_build` returns the same 3-tuple, and any provided limits are parsed and usable by callers/runner/subagents.
- Unit tests cover dict and string specs including invalid forms.

Test Plan
- Extend `tests/unit/inspect_agents/test_config_loader.py` with limits spec cases.
- Command: `CI=1 NO_NETWORK=1 PYTHONPATH=src:external/inspect_ai .venv/bin/pytest -q tests/unit/inspect_agents -k config_loader`.

Risks & Rollback
- Risk: behavior changes if supervisor starts using limits implicitly. Mitigation: keep supervisor limit handling out-of-scope; return parsed limits for explicit runner use.
- Rollback: keep parser unused; revert call sites.

---


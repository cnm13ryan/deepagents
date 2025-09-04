# TODO: YAML Config — Add Role Mapping for Sub‑Agents

## Context & Motivation
- Purpose: allow `role` indirection in YAML so environments control provider/model centrally; explicit `model` remains higher precedence.
- Problem: YAML supports only `model`; `resolve_model(role=...)` exists but can’t be used via config.
- Value: portable configs across local/CI/prod; fewer hard‑coded model strings.
- Constraints: maintain back‑compat; `model > role` precedence.

## Implementation Guidance
- Examine: `src/inspect_agents/config.py` (Pydantic `SubAgentCfg`, `build_from_config`), `src/inspect_agents/model.py` (resolver and role mapping), tests under `tests/unit/inspect_agents/`.
- Grep tokens: `class SubAgentCfg(BaseModel)`, `build_from_config(`, `resolve_model(`, `role: str`.
- Reference behavior: resolver rules and env precedence in `_resolve_role_mapping` and `resolve_model`.

## Scope Definition
- Implement: add `role: str | None` to `SubAgentCfg`. In `build_from_config`, if a sub‑agent has no `model` and has `role`, set `model = resolve_model(role=...)`.
- Preserve: explicit `model` wins over `role`.
- Tests: add tests for (a) explicit model; (b) role mapped via env; (c) remote provider without API key raises error.

## Success Criteria
- Behavior: YAML `role:` resolves to a valid Inspect model string; explicit `model` still dominates when present.
- Tests: new tests added; existing tests remain green.
- Docs: update config reference to document `role` and env keys `INSPECT_ROLE_<ROLE>_MODEL`/`_PROVIDER`.

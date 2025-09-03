# TODO — Model Roles Map: Implementation Checklists

> Self-contained, actionable to-do lists for each feature prompt.

---

## 1) Resolver Debug Trace (INSPECT_MODEL_DEBUG)

- [ ] Context & Motivation
  - [ ] Add a lightweight decision trace to model resolution to help debug role→model precedence in dev/CI.
  - [ ] Business value: faster diagnosis of misconfig; fewer support cycles.
  - [ ] Constraints: no behavior change; no heavy imports; avoid logging secrets.
- [ ] Implementation Guidance
  - [ ] Files: `src/inspect_agents/model.py` (function `resolve_model`, helper `_resolve_role_mapping`).
  - [ ] Grep: `resolve_model`, `INSPECT_EVAL_MODEL`, `INSPECT_ROLE_`, `DEEPAGENTS_MODEL_PROVIDER`.
  - [ ] Pattern: use `logging.getLogger(__name__).info({...})` once per call when `INSPECT_MODEL_DEBUG=1`.
  - [ ] Fields: `role`, `provider_arg`, `model_arg`, `role_env_model`, `role_env_provider`, `env_INSPECT_EVAL_MODEL`, `final`, `path`.
  - [ ] Dependencies: stdlib `logging` only.
- [ ] Scope Definition
  - [ ] Emit exactly one info log when `INSPECT_MODEL_DEBUG` truthy; none otherwise.
  - [ ] No functional changes; low overhead.
- [ ] Success Criteria
  - [ ] Unit tests (new): caplog asserts one record when flag set; none when unset.
  - [ ] No regressions in existing tests.

---

## 2) Repo-Level Role Defaults via pyproject.toml

- [ ] Context & Motivation
  - [ ] Allow teams to codify role defaults in-repo; env remains authoritative.
  - [ ] Value: reproducible CI; less per-dev env churn.
  - [ ] Constraints: stdlib only; cache reads; don’t slow hot path.
- [ ] Implementation Guidance
  - [ ] Files: `src/inspect_agents/model.py` (extend `_resolve_role_mapping` usage).
  - [ ] Grep: `_resolve_role_mapping`, `DEFAULT_ROLES`, `resolve_model`.
  - [ ] Add helper: `_load_repo_role_defaults(config_path: str | None) -> dict[str, tuple[str|None, str]]` using `tomllib`.
  - [ ] Config schema: `[tool.inspect_agents.roles]` supports either `role = "provider/model"` or `[tool.inspect_agents.roles.role] provider = "..."; model = "..."`.
  - [ ] Precedence: role env > repo toml > pass-through.
  - [ ] Testing knob: `INSPECT_ROLES_CONFIG_FILE` to point to a temp TOML.
- [ ] Scope Definition
  - [ ] Implement lazy, cached load; no new deps.
  - [ ] Use repo defaults only when env not set.
- [ ] Success Criteria
  - [ ] Unit tests cover repo-only, env-overrides, bare tag + provider, custom config path.
  - [ ] No behavior change when section absent.

---

## 3) Sub-Agent Role Wiring (config + builder)

- [ ] Context & Motivation
  - [ ] Let sub-agents declare a `role` instead of a concrete model.
  - [ ] Value: centralized role mappings; cleaner configs.
- [ ] Implementation Guidance
  - [ ] Files: `src/inspect_agents/config.py` (`SubAgentCfg`), `src/inspect_agents/agents.py` (`build_subagents`).
  - [ ] Grep: `SubAgentCfg`, `model=cfg.get("model")`, `react(`, `build_subagents`.
  - [ ] Add optional `role: str | None` to `SubAgentCfg`.
  - [ ] In `build_subagents`, if no `model` and `role` present, call `resolve_model(role=...)` and pass result to `react(..., model=...)`.
  - [ ] Preserve existing default sub-agent behavior.
- [ ] Scope Definition
  - [ ] Backward compatible; `model` takes precedence over `role`.
- [ ] Success Criteria
  - [ ] Integration test stubs `react` to assert it receives resolved model from role env.
  - [ ] No regressions in existing integration tests.

---

## 4) Strict Roles Mode and Unmapped Role Warnings

- [ ] Context & Motivation
  - [ ] Catch typos/invalid roles in stricter environments; optional warnings in dev.
  - [ ] Value: faster failure in prod/CI; better discoverability in dev.
- [ ] Implementation Guidance
  - [ ] Files: `src/inspect_agents/model.py` (`resolve_model`, `DEFAULT_ROLES`).
  - [ ] Grep: `DEFAULT_ROLES`, `inspect/` return path, `resolve_model`.
  - [ ] Env flags: `INSPECT_ROLES_STRICT=1` (raise on unmapped role), `INSPECT_ROLES_WARN_UNMAPPED=1` (log warn on fallback).
  - [ ] Optional allowlist: `INSPECT_ROLES_ALLOWLIST="researcher,coder,editor,grader,..."` (case-insensitive).
- [ ] Scope Definition
  - [ ] Only in `model.py`; default behavior unchanged without flags.
- [ ] Success Criteria
  - [ ] Unit tests: strict raises; warn logs once; allowlist accepted.

---

## 5) Robust Env Validation for Role Mapping

- [ ] Context & Motivation
  - [ ] Improve error messages for malformed `INSPECT_ROLE_<ROLE>_MODEL` values.
  - [ ] Value: clearer CI failures; faster resolution.
- [ ] Implementation Guidance
  - [ ] Files: `src/inspect_agents/model.py` (`_resolve_role_mapping`).
  - [ ] Grep: `_resolve_role_mapping`, `INSPECT_ROLE_`.
  - [ ] Validation: if value contains `/` but lacks a non-empty model segment (e.g., `openai/`), raise `RuntimeError` referencing the exact env var and expected formats.
  - [ ] Keep provider-specific checks in `resolve_model` as-is.
- [ ] Scope Definition
  - [ ] Minimal logic in `_resolve_role_mapping`; no behavior change for valid inputs.
- [ ] Success Criteria
  - [ ] Unit tests: malformed values raise with actionable messages; valid full path and provider+tag still pass.

---

## 6) Documentation & Templates for Roles

- [ ] Context & Motivation
  - [ ] Provide clear, copy-pasteable examples for role mapping via env and pyproject.
  - [ ] Value: faster onboarding; fewer support questions.
- [ ] Implementation Guidance
  - [ ] Files: `README.md`, `docs/adr/0002-model-roles-map.md`, `env_templates/inspect.env`.
  - [ ] Grep: `INSPECT_ROLE_`, `roles`, `pyproject`.
  - [ ] Content: env examples (`INSPECT_ROLE_RESEARCHER_MODEL=ollama/llama3.1`), split form (`..._PROVIDER` + `..._MODEL`), pyproject snippet under `[tool.inspect_agents.roles]`, precedence bullets, optional flags (`INSPECT_MODEL_DEBUG`, `INSPECT_ROLES_STRICT`, `INSPECT_ROLES_WARN_UNMAPPED`).
- [ ] Scope Definition
  - [ ] Docs-only changes; ensure examples match actual behavior.
- [ ] Success Criteria
  - [ ] Reviewed examples; markdown checks pass; template entries present in `env_templates/inspect.env`.

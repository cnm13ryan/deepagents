# ADR-0002: Model Roles Map — Env-Driven Resolution

## Context
Provide role-based model selection (e.g., researcher, coder, editor, grader) with environment overrides that resolve to concrete provider/model strings acceptable to Inspect (`react(model=...)`). Implementation landed in `resolve_model()` with role-aware env mapping.

## Goals
- Deterministic, debuggable resolution with minimal surprises.
- No provider secrets in code; env-first overrides.
- Keep pass-through to `inspect/<role>` working when no mapping is provided.

## Non‑Goals
- Introducing a new repo-wide config file in this change.
- Hard-coding opinionated model choices that require network/API keys.

## Decisions
- Support both env forms for each role (ROLE = uppercased, hyphens→underscores):
  - `INSPECT_ROLE_<ROLE>_MODEL`: may be a full provider path (`openai-api/lm-studio/qwen3`) or a bare tag (`llama3.1`).
  - `INSPECT_ROLE_<ROLE>_PROVIDER`: optional when the model is a bare tag (e.g., `ollama`, `openai`, `openai-api/lm-studio`).
- Resolution order (specific → general):
  1) Explicit `model` with provider prefix (contains `/`) → return as‑is.
  2) `role` present → if env mapping exists, resolve using role mapping; else return `inspect/<role>`.
  3) `INSPECT_EVAL_MODEL` if set to a concrete model (contains `/`) and not equal to `none/none` → use it.
  4) Provider: function arg → `DEEPAGENTS_MODEL_PROVIDER` → `ollama`.
  5) Provider-specific defaults/validation (API keys for remotes).
- Sentinel handling: treat `INSPECT_EVAL_MODEL=none/none` as “disabled” for step (3).

## Trade‑offs
- Fixed role set vs. dynamic roles
  - Fixed: predictability, typo detection; but less flexible. 
  - Dynamic (chosen): accepts any role; relies on env to opt-in mapping. Mitigation: document a recommended set and add optional strict mode later if needed.
- Single env vs. split provider+model
  - Single full path: simplest mental model; copy/paste friendly. 
  - Split: enables shared provider with per-role tags. Chosen: support both; precedence to full path.
- Repo defaults vs. pass‑through
  - Opinionated defaults: faster out‑of‑box; might surprise and carry maintenance cost. 
  - Pass‑through (chosen): safer; lets Inspect-native role routing work when present.
- Global `INSPECT_EVAL_MODEL` vs. role mapping precedence
  - Role mapping (chosen) overrides global; prevents a global from clobbering role-specific intent.

### Additional Considerations
- Debuggability: add `INSPECT_MODEL_DEBUG=1` to print resolution trace (role, source, final model) without secrets.
- Sentinel handling: treat `INSPECT_EVAL_MODEL=none/none` as disabled to avoid test/env contamination.
- Validation: for malformed role env values (e.g., missing tag), surface actionable errors that name the exact env var.
- Compatibility: keep lazy imports and environment-driven toggles to align with existing modules (tools, filters) that defer heavy imports and rely on env flags.

## Failure Modes & Errors
- Remote provider without required key → raise with actionable env name (e.g., `OPENAI_API_KEY`).
- Role set without model tag when provider requires one → raise guidance: set `<PROVIDER>_MODEL` or pass `model=`.
- Unknown role without mapping → return `inspect/<role>`; caller environment must handle or fail upstream.

## Observability & Debugging
- Recommend optional `INSPECT_MODEL_DEBUG=1` to emit decision trace (role used, mapping source, final model). Avoid logging secrets.
  This mirrors the project’s existing approach of structured, minimal logs in tools and filters.

## Examples
- `INSPECT_ROLE_RESEARCHER_MODEL=ollama/llama3.1` + `role="researcher"` → `ollama/llama3.1`.
- `INSPECT_ROLE_GRADER_MODEL=gpt-4o-mini` + `INSPECT_ROLE_GRADER_PROVIDER=openai` (with key) → `openai/gpt-4o-mini`.
- No role mapping; `INSPECT_EVAL_MODEL=openai-api/lm-studio/qwen3` → that value.

## Future Work (optional)
- Add repo config support (e.g., `pyproject.toml` under `[tool.inspect_agents.roles]`) with precedence: role env > repo config > pass‑through.
- Optional strict role allowlist (`INSPECT_ROLES_STRICT=1`) to catch typos early.
- Expand tests for precedence edges and malformed env values.

## Backward Compatibility
- Maintains existing behavior for callers not using roles or env; defaults to local Ollama when provider is unspecified.

---
Status: accepted
Decision date: 2025-09-03
Authors: deepagents

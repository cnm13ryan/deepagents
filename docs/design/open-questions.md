# Open Questions — Design Discussion

Status: living document. Last updated: 2025-09-04.

This page records design questions that need product/engineering decisions. Items include context, current behavior, options, trade‑offs, and proposed next steps. PRs should link the relevant section when introducing behavior that touches these topics.

## Filesystem/Sandbox — Consolidation of Utilities

Context
- We introduced `src/inspect_agents/fs.py` to unify filesystem configuration and sandbox helpers that were duplicated across `tools_files.py` and `tools.py`.
- Goals: single source of truth for mode/root/limits/timeouts parsing, sandbox preflight with TTL cache, symlink denial, and root confinement checks; minimize import coupling and avoid cycles.
- Constraint: preserve behavior, exception text, and log payloads; keep wrapper tools’ external behavior unchanged.

Current State
- New module `inspect_agents.fs` exists and is dependency‑light (stdlib, anyio, optional upstream exception type). Callers can adopt it incrementally via compatibility aliases (`_default_tool_timeout`, `_ensure_sandbox_ready`, etc.).
- `tools_files.py` now imports `fs` and overrides local helper bindings to route through the consolidated implementations while leaving the original helper bodies in place for now (risk‑free delegation). Follow‑up cleanup is pending.

### Q1 — Exceptions Source

Question
- Should `fs.py` import `ToolException` from `inspect_agents.exceptions` to guarantee a single exception type across modules?

Background
- Some tests and callers assert on `ToolException.message` or rely on consistent exception class identity. Today `fs.py` prefers the upstream type, with a local fallback, while other modules import from `inspect_agents.exceptions`.

Options
- A) Import from `inspect_agents.exceptions` inside `fs.py` and drop the local fallback. Ensures uniform type but adds a local dependency.
- B) Keep current approach (prefer upstream with fallback), and require callers to normalize at boundaries. Fewer intra‑repo deps; risk of mixed types.

Trade‑offs
- A avoids type fragmentation; a minor risk of cycles if `exceptions` later imports `fs`. B keeps `fs` more standalone but may complicate assertions.

Proposed Direction
- Prefer A (centralized exceptions). Verify no import cycle by keeping `exceptions` minimal and never importing `fs` from there.

Decision Needed
- Approve switching `fs.py` to `from inspect_agents.exceptions import ToolException`.

### Q2 — Logging Path for Preflight Warnings

Question
- Should `ensure_sandbox_ready()` log via `observability.log_tool_event(...)` to match existing payloads exactly, or keep the lightweight JSON logger in `fs.py`?

Background
- `tools_files.py` used `_log_tool_event` for `files:sandbox_preflight` warnings. `fs.py` currently emits an equivalent JSON payload directly to avoid importing local modules (cycle risk).

Options
- A) Route logging through `observability.log_tool_event` for perfect parity.
- B) Keep in‑module JSON logging with identical fields; rely on shared log ingestion.

Trade‑offs
- A guarantees identical formatting/filters but introduces a dependency edge. B keeps `fs` cycle‑free and simple; low risk if payload matches.

Proposed Direction
- Start with B (current). If observability requires central hooks (sampling, redaction), we can inject a logger callback from callers to avoid direct imports.

Decision Needed
- Confirm whether parity via observability hook is required now.

### Q3 — Public vs Underscore API Names

Question
- Do we keep both public (`truthy`, `fs_root`, `max_bytes`, ...) and underscore aliases (`_truthy`, `_fs_root`, `_max_bytes`, ...) or deprecate underscores?

Background
- Underscore names exist to minimize churn during migration. Long‑term, we want a clean public API.

Options
- A) Keep both until all callers migrate; then remove underscore forms with a deprecation window.
- B) Immediately switch all callers to public names and drop underscores.

Trade‑offs
- A enables incremental adoption with low risk. B reduces API surface faster but increases migration blast radius.

Proposed Direction
- A with a short deprecation plan (announce in release notes; remove underscore aliases after two minor versions).

Decision Needed
- Approve deprecation timeline for underscore aliases.

### Q4 — Duplicate Code Cleanup in `tools_files.py`

Question
- When should we remove the local helper implementations now shadowed by `fs` aliases?

Background
- `tools_files.py` currently overrides local helpers with `fs` bindings to ensure centralized behavior without removing code blocks yet.

Options
- A) Delete shadowed helper bodies now (small, targeted diff) and keep only the alias assignments.
- B) Keep bodies for one release as a rollback safety, with a comment pointing to `fs`.

Trade‑offs
- A reduces duplication immediately and prevents drift. B gives a safety net if we need to revert quickly.

Proposed Direction
- A (clean up now) given version control provides rollback; add a brief migration note in the PR.

Decision Needed
- Approve immediate removal of shadowed helpers.

### Q5 — `tools.py` Migration to `fs`

Question
- Should we switch `tools.py` helpers (`_truthy`, `_use_sandbox_fs`, `_default_tool_timeout`) to import from `fs` in the same refactor or as a follow‑up?

Background
- `tools.py` duplicates some FS helpers. Changing it is low risk but touches another module’s behavior.

Options
- A) Update `tools.py` now to import from `fs`.
- B) Follow‑up change with its own tests/validation.

Trade‑offs
- A reduces duplication immediately; slightly larger PR surface. B reduces change scope today but prolongs duplication.

Proposed Direction
- A, kept surgical (import + remove duplicates) and validated by existing tool behavior tests.

Decision Needed
- Approve migration of `tools.py` to `fs` helpers.

### Q6 — Unit Tests for `fs.py`

Question
- Should we add dedicated tests for `fs.py` (preflight TTL, `skip/force` modes, root confinement, symlink denial) now or after full migration?

Background
- Current tests exercise behavior via tools; targeted `fs` tests would improve signal and guard regressions.

Options
- A) Add focused tests now under `tests/inspect_agents/` with environment‑driven branches.
- B) Defer until callers fully adopt `fs` to avoid churn in expectations.

Trade‑offs
- A increases confidence immediately; minimal maintenance cost. B keeps this PR smaller but leaves a coverage gap.

Proposed Direction
- A. Keep tests deterministic (`NO_NETWORK=1`), stub tool modules for sandbox stubs, and assert log payloads/exception messages.

Decision Needed
- Approve adding an `fs` test module in the next change.

### Q7 — Documentation Updates

Question
- Should we update docs to point to `inspect_agents.fs` as the canonical source for FS behavior and environment knobs?

Background
- Existing docs reference behavior spread across multiple modules. Centralizing improves discoverability.

Options
- A) Update references in How‑To/Reference pages to link to this consolidation and the env variables.
- B) Keep current docs and update later post‑migration.

Trade‑offs
- A reduces confusion immediately; small doc changes. B risks stale guidance.

Proposed Direction
- A. Add a short “Design Note” in Filesystem How‑To and Reference pages linking to this section.

Decision Needed
- Approve doc updates in the next doc PR.

---

## Filesystem Sandbox — Read‑only Mode (new)

Context
- We plan a read‑only mode in sandbox (`INSPECT_AGENTS_FS_READ_ONLY=1`) where write/edit/delete are blocked while listing and reading remain allowed. This is referenced from the Environment reference.

Open Points
- Error taxonomy and message text (`ToolException("SandboxReadOnly")` vs richer message).
- Observability payload shape (include `mode`, `fs_root`, and attempted operation?).
- Interaction with preflight `force` mode and typed result toggles.

Next Steps
- Finalize error/message contract and add tests covering ls/read allowed and write/edit/delete denied with correct logs/fields.

#
# Open Questions — Side‑Effect Tool Application Helper (Migration)

Context
- We extracted the inline logic in `create_deep_agent` that applies side‑effecting tool calls when a `submit` appears in the same turn. The new helper `_apply_side_effect_calls(messages, tools)` locates the latest assistant message with tool calls, excludes `submit`, replays via `execute_tools`, and then applies defensive Store fallbacks for `write_file` and `write_todos`. The behavior and signature of `create_deep_agent` remain unchanged.

Current State
- Helper lives in `src/inspect_agents/migration.py` and is invoked immediately after the base ReAct agent returns messages.
- Fallback mirrors only `write_file` and `write_todos`; other tools are not mirrored.
- Exceptions are swallowed to preserve best‑effort semantics identical to pre‑extraction logic.

Why it matters
- Extracting this logic enables unit testing and safer maintenance of the migration shim, but raises policy and API questions (visibility, scope of fallbacks, approvals, and typing) that should be decided explicitly.

### Q1 — Helper Visibility (private vs. exported)

Question
- Should `_apply_side_effect_calls` remain private or be exported in `__all__` and documented as part of the migration surface?

Options
- Private (status quo): minimal public surface; tests can still import it directly but risk churn.
- Exported: stable for external reuse; increases long‑term API commitment.

Recommendation
- Keep private for now; promote to public if external adoption emerges.

Acceptance Criteria
- Decide visibility and reflect it in `__all__`, docs, and tests.

### Q2 — Helper Location (module placement)

Question
- Keep the helper in `migration.py` or move to a dedicated `migration_utils.py` (or `migration/_side_effects.py`)?

Trade‑offs
- Collocation improves discoverability and keeps related logic together; a separate module clarifies reuse and keeps the file smaller.

Recommendation
- Keep in `migration.py` until an additional caller appears; then extract.

Acceptance Criteria
- Confirm location; if moved, update imports and docs.

### Q3 — Fallback Scope (which tools to mirror)

Question
- Should the fallback include more side‑effect tools (e.g., `update_todo_status`, file edits) beyond `write_file` and `write_todos`?

Trade‑offs
- Expanding increases resilience when `execute_tools` is skipped, but risks duplicating tool logic and widening blast radius.

Recommendation
- Keep minimal scope; add new cases only with concrete requirements and tests.

Acceptance Criteria
- Enumerate tools to mirror, add tests, and document rationale.

### Q4 — API Shape and Typing

Question
- Should the helper be strictly typed (e.g., `list[ChatMessage]`, `Sequence[Tool|ToolDef|ToolSource]`) instead of `list[Any]` / `Sequence[object]`?

Trade‑offs
- Stronger typing aids tooling but may introduce tighter coupling or import cycles.

Recommendation
- Keep dynamic typing until the API stabilizes; revisit later.

Acceptance Criteria
- Decide typing strictness; if tightened, update annotations and add type‑focused tests.

### Q5 — Error Reporting and Observability

Question
- The helper swallows exceptions. Should it emit debug‑level logs (e.g., when replay fails or fallback applies)?

Recommendation
- Add low‑noise debug logs under an `inspect_agents.migration` logger, preserving user‑visible behavior.

Acceptance Criteria
- Define log fields/levels; add a test asserting a log entry in failure/fallback paths.

### Q6 — Approvals and Policy Interplay

Question
- If `execute_tools` fails due to approval denial, should the fallback still apply (potentially bypassing the approval intent)?

Options
- Always fallback (status quo).
- Policy‑aware fallback: skip fallback on approval denials; only apply on timeouts/offline conditions.

Recommendation
- Make fallback policy‑aware when approvals are active; propagate minimal failure context from `execute_tools` to the helper to decide.

Acceptance Criteria
- Specify allowed fallback conditions; add tests simulating approval denials to ensure no Store mutation occurs.

### Q7 — Idempotency and Double‑Application

Question
- The helper runs `execute_tools` and then attempts fallbacks; this can double‑apply effects.

Recommendation
- If `execute_tools` returns tool messages (or transcript shows success), skip fallbacks.

Acceptance Criteria
- Implement a success check and add tests to cover both branches.

### Q8 — Instance Scoping for Store Models

Question
- Should the fallback accept an optional `instance` and pass it to `store_as(...)` to isolate per‑agent state?

Trade‑offs
- Default instance preserves back‑compat; explicit instance improves isolation but requires plumbing through the call path.

Recommendation
- Keep default instance now; consider parameterization if multi‑agent isolation is needed.

Acceptance Criteria
- Decide scoping; if parameterized, update callers and tests.

### Q9 — Limits and Large Content

Question
- Should fallback writes enforce size limits comparable to tool‑path output limits?

Recommendation
- Respect a conservative cap (aligned with existing limits) in fallback to avoid unbounded Store writes.

Acceptance Criteria
- Define the limit and behavior on exceed (clip vs. error); add tests.

### Q10 — Test Coverage Extensions

Gaps / Candidates
- Unknown tools, malformed arguments, multiple assistant tool messages, approval denials, very large content, duplicate writes, handoff‑exclusive interactions, concurrent tool calls.

Acceptance Criteria
- Prioritize and add targeted tests; keep deterministic/offline by default.

---

## Iterative Agent Docs & CLI — Open Questions (new)

### Q1 — Supervisor Flags Coverage

Question
- Should we document `examples/inspect/run.py` flags alongside the Iterative Agent reference, or keep supervisor content separate?

Background
- The Iterative Agent reference now includes CLI usage for `examples/research/run_iterative.py`, `run_profiled.py`, and the Inspect task. The supervisor demo (`examples/inspect/run.py`) exposes provider/model and standard tool toggles but is not covered in that page.

Options
- A) Add a short “Supervisor Runner” subsection under the Iterative Agent reference’s CLI section.
- B) Create a separate Supervisor reference and link both directions.

Trade‑offs
- A improves discoverability with minimal sprawl but mixes concerns; B keeps conceptual boundaries clear but adds another page to maintain.

Proposed Direction
- A. Add a compact subsection now; revisit a dedicated Supervisor page if scope grows.

Decision Needed
- Approve adding a supervisor subsection to the Iterative Agent reference.

### Q2 — Docs Placement (Getting Started vs Reference)

Question
- Should key Iterative Agent flags/workflows appear in Getting Started, or remain only in Reference?

Background
- Examples link to the reference page for flags; Getting Started currently lacks an iterative quick‑start snippet.

Options
- A) Add a small Getting Started card with a 3‑line example and a link to the reference.
- B) Keep flags only in the reference to avoid duplication.

Trade‑offs
- A increases approachability but can drift from reference; B avoids drift but may slow first‑time onboarding.

Proposed Direction
- A. Add a single short example and a link; no inline flag tables in Getting Started.

Decision Needed
- Approve adding the Getting Started card and link.

### Q3 — Default Budgets (Time/Steps)

Question
- Should we standardize `time_limit`/`max_steps` defaults across runners and examples?

Background
- `run_iterative.py` and `iterative_task.py` default to 600s/40 steps; `run_profiled.py` defaults to 120s/20 steps. Docs examples now commonly show 300s/20 steps for snappier runs.

Options
- A) Unify all scripts at 300s/20.
- B) Keep script defaults (600/40 for general, 120/20 for profiled) but standardize docs at 300/20.
- C) Unify all scripts at 600/40 and advise users to lower via flags for quick runs.

Trade‑offs
- Short budgets speed iteration but risk truncation; longer budgets improve result quality but cost time/resources.

Proposed Direction
- B. Standardize documentation examples at 300/20; revisit script defaults after user feedback.

Decision Needed
- Approve documentation standard of 300/20 and defer script changes.

### Q4 — CI/Test Scope for Docs‑Only PRs

Question
- What subset of tests should run automatically for docs‑only changes?

Background
- We’ve been running targeted unit subsets locally (e.g., `tests/unit/inspect_agents -k iterative`) due to sandbox constraints and time budgets.

Options
- A) Add a docs‑only CI job that runs a fast unit subset offline plus a link checker.
- B) Skip tests on docs‑only PRs and rely on maintainers to opt‑in runs.

Trade‑offs
- A increases confidence with modest CI cost; B is cheaper but risks unnoticed drift.

Proposed Direction
- A. Add a unit subset (`iterative or tools or logging`), offline env, `--maxfail=1`.

Decision Needed
- Approve adding the docs‑only CI job.

### Q5 — CLI Quick Reference Table

Question
- Should the Iterative Agent reference include a compact flag table at the top?

Background
- The page contains prose and examples; a table may speed scanning for experienced users.

Options
- A) Add a two‑column table (Flag → Description/Default) for core flags and task `-T` equivalents.
- B) Rely on prose/examples and `--help` output.

Trade‑offs
- Tables can drift from CLI help; prose is harder to scan.

Proposed Direction
- A. Add the table with a note that `--help` is the source of truth.

Decision Needed
- Approve adding the quick‑reference table.

### Q6 — Cross‑Linking Between Reference and Examples

Question
- Where should backlinks live for best navigation?

Background
- Examples link to the reference; the reference can add a “See Also” section to point to research runners and the Inspect task.

Options
- A) Add a short “See Also” at the bottom of the reference with 2–3 high‑value links.
- B) Add inline links next to each CLI subsection heading.

Trade‑offs
- A keeps the page clean; B increases inline navigation but can be noisy.

Proposed Direction
- A. Add a concise “See Also” block.

Decision Needed
- Approve adding the “See Also” links.

### Q7 — Additional Example: `INSPECT_MAX_TOOL_OUTPUT`

Question
- Should we include a sample command setting the global tool‑output cap in the examples?

Background
- The reference documents `INSPECT_MAX_TOOL_OUTPUT`; examples do not yet show it in command lines.

Options
- A) Add one example using `INSPECT_MAX_TOOL_OUTPUT=8192` with a short note on provider behavior and wrappers.
- B) Keep this detail in configuration prose only.

Trade‑offs
- A improves visibility of limits; risks implying provider‑uniform behavior where differences exist.

Proposed Direction
- A. Add a single example with a cautionary note and link to provider/tool specifics.

Decision Needed
- Approve adding the example to the Iterative Agent reference.

---

## Model Resolver Diagnostics (`resolve_model_explain`) — Open Questions

Context (2025-09-04)
- We added `resolve_model_explain(provider=None, model=None, role=None)` which returns `(model_id, explain_dict)` for deterministic testing and debugging without scraping logs. The dict mirrors `_log_model_debug` fields and includes `path`. This preserves `resolve_model(...)` behavior and logging. See `src/inspect_agents/model.py` for the helper `_resolve_model_core(...)` and the public function.  

Why this matters
- Tests and operators need structured, assertion-friendly insight into how a model was resolved: which inputs were considered, where each choice came from (arg/env/default/role), and which branch produced the final value.
- Stabilizing the debug surface avoids brittle log scraping and provides hooks for CI and support tooling.

### 1) What fields belong in the explain dict by default?

Current
- Explain dict contains: `path`, `provider_arg`, `model_arg`, `role_env_model`, `role_env_provider`, `env_inspect_eval_model`, plus `final` (added on return).

Options
- Minimal (status quo): keep only inputs + `path` + `final`.
- Enriched: add normalized, post-resolution fields and sources:  
  - `provider_effective` (normalized provider actually used)  
  - `provider_source` (`arg|env|default|role-map`)  
  - `model_effective` (bare tag used in provider-specific branches when applicable)  
  - `model_source` (`arg|env|role-map|inspect-eval`)  
  - Echo `role` for downstream assertions.

Recommendation
- Adopt Enriched; keep existing keys for backward compatibility and add new keys with stable semantics.

Acceptance Criteria
- Add the enriched keys; update reference docs; add unit tests asserting values and `*_source` labels across explicit, role-map, INSPECT_EVAL_MODEL, and provider branches.

### 2) Error explainability — how to surface context on failures?

Current
- `RuntimeError` is raised for missing API keys or tags on remote providers; message is human-readable but unstructured.

Options
- Keep plain exceptions.  
- Introduce `ModelResolutionError` carrying `.explain` (dict) and `.reason` (`missing_api_key|missing_model|invalid_provider|...`).

Recommendation
- Introduce `ModelResolutionError` while preserving message text; keep `resolve_model()` return type unchanged.

Acceptance Criteria
- Replace `RuntimeError` raises with `ModelResolutionError(reason=..., explain=...)`; add tests for missing API key (openai), missing model (openai), and `openai-api/<vendor>` missing vendor key.

### 3) Path label stability — public contract or best-effort?

Current
- Labels include: `explicit_model_with_provider`, `role_env_mapping`, `role_inspect_indirection`, `env_INSPECT_EVAL_MODEL`, `provider_ollama`, `provider_lm_studio`, `provider_<remote>`, `provider_openai_api_<vendor>`, `fallback_model_with_provider`, `final_fallback_ollama`.

Options
- Treat as internal (no guarantees).  
- Freeze as public; only additive changes; deprecations documented.

Recommendation
- Freeze current set as public; allow additive changes only; document deprecations with a minor version bump.

Acceptance Criteria
- Document label list; add a smoke test asserting label membership for common scenarios.

### 4) Source granularity — record where each decision came from?

Current
- Not explicitly recorded beyond raw inputs.

Options
- Add `provider_source`, `model_source`, `role_source`, and `inspect_eval_source` (`unset|sentinel|set`).

Recommendation
- Add these keys; high debug value, low cost.

Acceptance Criteria
- Tests assert `*_source` values for arg/env/default/role-map branches.

### 5) Sentinel handling for `INSPECT_EVAL_MODEL=none/none`

Current
- Sentinel disables the env override but is not explicitly surfaced beyond omission.

Options
- Add `inspect_eval_disabled: bool` and `env_inspect_eval_model_raw`.

Recommendation
- Add both; keep `env_inspect_eval_model` as the effective value or `None`.

Acceptance Criteria
- Test that with `none/none`, `inspect_eval_disabled is True`, `env_inspect_eval_model is None`, and `*_raw == "none/none"`.

### 6) Type shape — dict vs typed object

Current
- Return type is `(str, dict)`.

Options
- Keep dict; add `TypedDict` for static typing.  
- Switch to `NamedTuple`/`@dataclass` (breaking change) or provide an optional wrapper factory.

Recommendation
- Add a `TypedDict` and keep returning a dict; optionally expose a dataclass factory without changing the default return.

Acceptance Criteria
- Type stubs + mypy annotations; docs list keys and meanings.

### 7) Test coverage — offline-safe additions

Gaps
- Remote providers with placeholder keys, `openai-api/<vendor>` branch, and sentinel case.

Plan
- Add tests for: `openai` with fake key; `openai-api/lm-studio` with fake key/model; sentinel `none/none`; role-map with provider split; fallback with bare model. Ensure `NO_NETWORK=1`.

Acceptance Criteria
- Deterministic pass with no network; failures report specific `path` and `*_source`.

### 8) Docs placement — where to teach debugging

Current
- Brief note exists in `docs/reference/environment.md` under Providers & Models.

Options
- Add a short “Debugging model resolution” page under `docs/how-to/`.  
- Add an example in `examples/research/README.md`.

Recommendation
- Do both; keep the how-to concise and link to reference and examples.

Acceptance Criteria
- New how-to exists; examples updated; cross-links present from the reference page.

Related files
- Implementation: `src/inspect_agents/model.py` (resolver + explain helper).  
- Tests: `tests/unit/inspect_agents/model/test_model_explain.py`, `tests/unit/inspect_agents/model/test_model.py`.  
- Docs: `docs/reference/environment.md` (reference note), this file.

---

# Settings and Env Centralization — Open Questions (2025‑09‑04)

Context
- We introduced `src/inspect_agents/settings.py` to centralize common env/flag parsing and reduce drift across modules. Internal helpers in `tools.py`, `tools_files.py`, `filters.py`, and `approval.py` now delegate to it via aliases that preserve historical underscore names for test monkeypatching.

## 1) Filters aliasing vs wrapper for `_truthy`

- Current state: `filters.py` assigns `_truthy = settings.truthy` (no redefinition).
- Why it matters: tests patch `_truthy`; aliasing avoids code duplication and drift.
- Options:
  - A) Keep alias (status quo).
  - B) Replace with a wrapper function calling `settings.truthy(val)`.
- Recommendation: A) keep alias — minimal surface, fully patchable.
- Exit criteria: Document policy in `docs/reference/environment.md`; avoid redefining `_truthy` elsewhere.

## 2) Iterative helpers migration (`iterative_config.py`)

- Current state: local `_parse_int_opt` returns `None` for non‑positive values; semantics differ slightly from `settings.int_env` with `minimum`.
- Why it matters: we must not change meaning of “disabled” (<=0 → None) when consolidating.
- Options:
  - A) Leave as‑is.
  - B) Add tiny wrappers that call `settings.int_env` then convert `<=0` → None.
  - C) Extend `settings.int_env` with a `none_if_leq` option and adopt it.
- Recommendation: B) wrappers in `iterative_config.py` now; consider C) if pattern repeats elsewhere.
- Exit criteria: wrappers in place; iterative tests green with unchanged behavior.

## 3) `str_env` empty‑string semantics

- Current state: `str_env(name, default)` returns empty string if set; only uses default when unset.
- Why it matters: some call-sites may want “empty means unset”.
- Options:
  - A) Keep current behavior universally (empty ≠ unset).
  - B) Add `str_env_or_none(name)` that collapses empty/whitespace to None; use selectively.
- Recommendation: A) keep; introduce B) only when needed by real callers.
- Exit criteria: document rule; audit provider selection code paths.

## 4) Filesystem knobs centralization

- Current state: FS envs (`INSPECT_AGENTS_FS_MODE`, `_FS_ROOT`, `_FS_MAX_BYTES`, `_FS_READ_ONLY`) live in FS modules to avoid cycles and keep sandbox logic cohesive.
- Options:
  - A) Keep local (status quo).
  - B) Move pure getters to `settings` and import from FS code.
- Risks: potential import cycles and heavier import‑time behavior.
- Recommendation: A) keep local; revisit B) after confirming no cycles and measuring impact.
- Exit criteria: rationale documented; no duplicate FS parsing outside FS modules.

## 5) Tool‑output cap (`INSPECT_MAX_TOOL_OUTPUT`) accessor

- Current state: parsed in multiple places (observability, iterative) with defensive merges into Inspect `GenerateConfig`.
- Proposal: add `settings.max_tool_output_env() -> int | None` parsing non‑negative ints (0 allowed) and returning None when unset/invalid.
- Recommendation: add accessor; adopt in both call sites without changing precedence (explicit arg/active config still beat env).
- Exit criteria: unified accessor in place; limit/truncation tests remain green.

## 6) Unit tests for `settings`

- Current state: behavior covered indirectly; no direct tests for helpers.
- Action: add `tests/unit/inspect_agents/config/test_settings.py` covering `truthy`, `int_env` (min/max and invalid), `float_env` (invalid), `str_env`, `typed_results_enabled`, `default_tool_timeout`.
- Exit criteria: tests green offline; examples documented in `tests/README.md`.

## 7) Deprecation path for underscore helpers

- Current state: underscore names remain as import aliases for patchability.
- Recommendation: soft‑deprecate in comments; prefer `settings.*` in new code; keep aliases long‑term to avoid breaking tests.
- Exit criteria: internal call‑sites use `settings.*`; aliases retained for back‑compat.

## 8) Documentation touchpoints

- Current state: `settings.py` exists; not yet surfaced in docs.
- Actions: add an “Environment & Settings” section to `docs/reference/environment.md`; cross‑link from quickstart and approvals how‑to.
- Exit criteria: docs updated; code snippets use `settings.*`.

# Open Questions — ADR 0005: Tool Parallelism and Handoff Exclusivity

Last updated: 2025-09-03

Scope: Tracks outstanding decisions related to ADR 0005’s delivery plan. v1 (approval‑policy enforcement) is shipped; v2 (optional executor pre‑scan) is proposed. See ADR context, decision, and trade‑offs. 〖F:docs/adr/0005-tool-parallelism-policy.md†L16-L31〗 〖F:docs/adr/0005-tool-parallelism-policy.md†L45-L69〗

References:
- v1 policy implementation: `handoff_exclusive_policy()` enforces “first handoff wins” by approving only the first handoff call and rejecting all other tool calls in the same assistant turn; also logs a local tool event for observability. 〖F:src/inspect_agents/approval.py†L195-L279〗
- ADR trade‑offs (policy visibility vs executor guarantees) and v2 outline. 〖F:docs/adr/0005-tool-parallelism-policy.md†L58-L69〗

---

## 1) Flag name and semantics for v2 opt‑in (executor pre‑scan)

- Problem: We need a clear, future‑proof env flag to enable executor‑level pre‑scan that selects the first handoff and avoids enqueuing all other tool calls for that assistant turn. 〖F:docs/adr/0005-tool-parallelism-policy.md†L53-L55〗

- Options:
  - `INSPECT_EXECUTOR_PRESCAN_HANDOFF=1` (explicit scope + behavior)
  - `INSPECT_PRESCAN_HANDOFF=1` (shorter; less precise)
  - `INSPECT_TOOLCALL_PRESCAN_HANDOFF=1` (very explicit; verbose)

- Selection criteria:
  - Clarity and discoverability alongside `INSPECT_DISABLE_TOOL_PARALLEL`. 〖F:docs/adr/0005-tool-parallelism-policy.md†L29-L31〗
  - Forward compatibility if pre‑scan later expands beyond handoffs.
  - Orthogonality to performance flags (serial vs parallel) and approval presets.

- Recommendation (pending approval): Use `INSPECT_EXECUTOR_PRESCAN_HANDOFF=1` with default off. Rationale: mirrors the locus of control (executor), is grep‑friendly, and remains accurate if policy logic evolves. No behavior change when unset; v1 remains the default. 〖F:docs/adr/0005-tool-parallelism-policy.md†L49-L56〗

- Open point: If we later add pre‑scan for other exclusivity classes, consider a generalized `INSPECT_EXECUTOR_PRESCAN=*` with comma‑separated features (e.g., `handoff`).

Decision needed by: 2025‑09‑10.

---

# Approvals — Default Activation for Handoff Exclusivity (ADR 0005 v1)

Context
- ADR 0005 shipped a policy that enforces “first handoff wins” via an approval policy (`handoff_exclusive_policy()`); today this is opt‑in and not wired into presets. The question is whether to activate it by default in our approval presets (ci/dev/prod) or leave it fully opt‑in per run/config.

Problem
- Inconsistent defaults lead to surprising multi‑tool execution during handoffs in dev/prod unless the caller explicitly installs the policy. Teams may expect exclusivity out‑of‑the‑box after reading ADR 0005.

Options
- Option A — Enable in `dev` and `prod` presets; keep `ci` permissive. Pros: safer defaults in interactive/dev and deployments; preserves CI flexibility. Cons: behavior change for existing users of presets.
- Option B — Keep opt‑in; document prominently in guides and examples. Pros: no change in behavior. Cons: drift from ADR intent in default experiences.
- Option C — New preset `dev_strict` that includes exclusivity; leave existing presets unchanged.

Decision: Adopted Option A on 2025‑09‑04.
- `approval_preset("dev")` and `approval_preset("prod")` now include `handoff_exclusive_policy()` by default; `ci` remains permissive.
- Docs updated in `docs/how-to/approvals.md`; opt‑out guidance: build a custom policy list or start from `ci` and add rules.

References
- Policy implementation: `handoff_exclusive_policy()` enforces exclusivity at approval layer (v1).  
  Source: src/inspect_agents/approval.py.

---

# Config — Sub‑Agent Role Mapping in YAML

Context
- Today `SubAgentCfg` accepts a concrete `model`. We want to optionally accept a `role` and resolve to a model via `resolve_model(role=...)`, keeping `model` > `role` precedence and enabling env/pyproject role mapping work tracked in the backlog.

Problem
- Configs hard‑code models, reducing portability between local/CI/prod where providers differ. A role indirection keeps configs portable and allows centralized env policy.

Options
- Option A — Add `role: str | None` to `SubAgentCfg`; when `model` is absent, call `resolve_model(role=...)` during `build_subagents`. Preserve existing behavior otherwise.
- Option B — Leave YAML unchanged; require callers to resolve roles externally and pass concrete `model`.

Recommendation (pending approval)
- Option A; minimal change, backwards compatible, and aligns with the model‑roles backlog.

Decision Needed
- Approve schema change and precedence; green‑light tests/docs to demonstrate role‑based sub‑agents.

References
- Resolver precedence and env keys live in src/inspect_agents/model.py; `SubAgentCfg` defined in src/inspect_agents/config.py.

---

# Sandbox Guardrails — Minimal Test Matrix (Root, Symlink, Delete, Size)

Context
- Files tool enforces sandbox root confinement, symlink denial, delete disabled in sandbox, and a byte ceiling across modes. We need an agreed, offline‑friendly test matrix to keep these guarantees durable.

Problem
- CI environments may not provide a running sandbox service; tests must pass offline while still validating behaviors.

Options
- Option A — Pure offline tests using the in‑memory store plus in‑process stubs to simulate sandbox transport presence, asserting:
  - Root confinement rejects paths outside `INSPECT_AGENTS_FS_ROOT` when sandbox is “available”.
  - Symlink denial via a simulated bash_session response.
  - Delete disabled in sandbox; enabled/idempotent in store.
  - Byte ceiling errors for read/write/edit with small configured limits.
- Option B — Dual‑layer: keep A as baseline; add optional integration tests behind a marker when a sandbox is available (skipped by default in CI).

Recommendation (pending approval)
- Option B; ship A now, add a `sandbox` pytest marker for opt‑in integration.

Decision Needed
- Approve baseline assertions and skip strategy; define acceptable lower bounds for coverage.

References
- Guardrails implemented in src/inspect_agents/tools_files.py.

---

# Conversation Pruning — Defaults, Scope, and Observability

Context
- A new lightweight `prune_messages()` helper was added and integrated into the iterative agent to bound history growth (keep all system, first user, and last N messages with tool pairing). Length‑based only; no tokenizer.

Open Questions
- Defaults: are `prune_after_messages=120` and `prune_keep_last=40` appropriate across workloads?
- Scope: should pruning also apply to the react supervisor path or remain iterative‑only?
- Unification: remove the older in‑file `_prune_history` logic and use `prune_messages()` everywhere for a single behavior?
- Observability: emit a lightweight `prune_event` (pre→post counts) to logs for diagnose‑ability, or keep silent unless debugging is enabled?
- Configuration: add env toggles `INSPECT_PRUNE_AFTER_MESSAGES` and `INSPECT_PRUNE_KEEP_LAST` with sensible bounds?

Recommendation (pending approval)
- Keep current conservative defaults; add optional env toggles; emit a single info log when `INSPECT_MODEL_DEBUG` (or a new `INSPECT_PRUNE_DEBUG`) is set.

Decision Needed
- Confirm defaults, scope (iterative‑only vs global), and logging approach.

References
- Utility: src/inspect_agents/_conversation.py. Integration points: src/inspect_agents/iterative.py.

---

# Token‑Aware Pruning — Future Option and Flags

Context
- Length‑based pruning is robust and provider‑agnostic but can be sub‑optimal relative to token budgets. A token‑aware path could use provider metadata while keeping a soft dependency model.

Options
- Option A — Add an optional token‑aware strategy that estimates tokens using Inspect’s model utilities when present; fall back to length‑based.
- Option B — Stay length‑only; defer token work to provider‑specific runners.

Recommendation (pending approval)
- Option A, behind a flag, documented as “best‑effort”, with guardrails to avoid tight coupling. Add environment knobs (e.g., `INSPECT_PRUNE_TOKEN_BUDGET`) and a minimum floor to prevent over‑pruning.

Decision Needed
- Approve roadmap and flag names; decide default off/on for dev.

References
- Iterative agent integration and pruning utility named above.

---
# Iterative Agent — Pruning, Termination, and Public Surface (New)

Last updated: 2025‑09‑04

Context
- The `build_iterative_agent(...)` now avoids provider‑specific exceptions, adds bounded history pruning, and surfaces configuration for progress cadence and optional keyword termination.  It remains submit‑less and uses the active Inspect model by default.  Signature and parameters are documented inline. 〖F:src/inspect_agents/iterative.py†L70-L81〗 〖F:src/inspect_agents/iterative.py†L96-L107〗 〖F:src/inspect_agents/iterative.py†L191-L201〗 〖F:src/inspect_agents/iterative.py†L233-L242〗
- The pruning helper keeps the first system + first user message and the last window of turns, while dropping orphan tool messages. 〖F:src/inspect_agents/iterative.py†L120-L171〗
- `build_iterative_agent` is now re‑exported via `inspect_agents.agents` for a consistent public surface alongside `build_supervisor`. 〖F:src/inspect_agents/agents.py†L141-L152〗 〖F:src/inspect_agents/agents.py†L161-L170〗

Open Questions
1) Pruning defaults — turns vs messages
   - Problem: `max_turns=50` keeps the last ≈2×turns messages (assistant/tool/user mix), which is robust but heuristic.  Should we offer a messages‑based cap (`max_messages`) in addition to `max_turns`?
   - Options: (A) keep `max_turns` only; (B) add `max_messages` (higher precedence when set); (C) expose both but default to turns.
   - Considerations: determinism across providers, tool burstiness, simplicity of mental model.
   - Recommendation (pending): (B) add `max_messages` as an opt‑in; keep `max_turns=50` default.

2) Progress pings and pruning order
   - Problem: Progress pings (“Info: HH:MM:SS elapsed”) aid observability but could consume space in the retained tail.  Should pruning prefer dropping pings first? 〖F:src/inspect_agents/iterative.py†L191-L201〗
   - Options: (A) treat pings like any user message (status quo); (B) detect and preferentially drop them during pruning; (C) gate with `progress_every=0` to disable.
   - Recommendation (pending): Keep (A) for simplicity; document (C) for tight contexts.

3) Keyword‑based termination (opt‑in only)
   - Problem: Keyword stops are brittle; default is off (`stop_on_keywords=None`).  Validate the opt‑in list and restrict matching to assistant text only (status quo). 〖F:src/inspect_agents/iterative.py†L276-L283〗
   - Decision: Keep default off; no change needed unless users request canned sets.

4) Provider coupling avoidance
   - Problem: Ensure we remain provider‑agnostic.  We removed the OpenAI‑specific `LengthFinishReasonError`; detection now relies on `stop_reason=="model_length"` or a generic overflow path.  Are there providers that use alternative stop reason fields?
   - Action: Audit providers used in this repo; if divergence exists, add a small compatibility shim documented in code comments. 〖F:src/inspect_agents/iterative.py†L220-L231〗 〖F:src/inspect_agents/iterative.py†L233-L242〗

Decision Needed
- Add `max_messages`? Preferentially drop progress pings? Target: 2025‑09‑10.

---

# Files Tool Exposure vs Wrappers in Supervisor (New)

Context
- Docs position `files` as the canonical unified API, with `ls/read_file/write_file/edit_file/delete_file` as wrappers. 〖F:docs/tools/README.md†L9-L21〗
- Supervisor built‑ins currently expose the wrapper tools but not the `files` tool directly. 〖F:src/inspect_agents/agents.py†L79-L93〗

Open Question
- Should `files_tool()` also be exposed by default in the supervisor to align docs with runtime, or should docs explicitly state that wrappers are what agents receive by default?

Options
- A) Expose `files` alongside wrappers by default (no behavior change for wrappers; enables unified usage).
- B) Keep wrappers only; update docs to clarify exposure vs canonical reference.

Recommendation (pending)
- B) Keep wrappers only to minimize surface duplication; add a one‑line note in Tools README about exposure defaults.

Decision Needed
- Choose A or B; if B, add a short doc note. Target: 2025‑09‑08.

---

# Limits Observability — Runner vs Handoff Scope (New)

Context
- We want consistent, machine‑parseable logs when limits are nearing (≥80%) or exceeded. Runner limits are straightforward; handoff‑level limits are applied inside `handoff(...)` and are harder to centralize.

Problem
- Where to emit “limit_nearing/limit_exceeded” events and how to avoid noisy/duplicated logs across scopes.

Options
- Option A — Runner‑only in v1: emit JSON logs at the end of a sample using Inspect’s `sample_limits()` and transcript events. Pros: simple, low noise. Cons: no immediate handoff‑scope signals.
- Option B — Runner + Handoff: add a wrapper/hook around `handoff(..., limits=[...])` to emit scope=`handoff` events when thresholds are crossed. Pros: granular visibility. Cons: higher coupling and risk of duplication.

Recommendation (pending)
- Start with Option A (runner‑only), then add a minimal hook for handoffs in v2 with deduplication guards.

Event Schema (proposed)
- `event`: `limit_nearing | limit_exceeded`
- `scope`: `runner | handoff`
- `limit_kind`: `time | tokens | messages | tools`
- `threshold`, `used`, `remaining`, `agent_name` (optional for runner), `handoff_name` (handoff only).

Decision Needed
- Approve Option A for v1; define the handoff hook location for v2. Target: 2025‑09‑12.

---

# YAML Limits: Parser vs Runner Responsibility (New)

Context
- The config model contains `limits` at the root, but `build_from_config` returns `(agent, tools, approvals)` without applying or returning limits; guides mark YAML limits as “illustrative spec; bind via Python”. 〖F:src/inspect_agents/config.py†L32-L37〗 〖F:src/inspect_agents/config.py†L115-L123〗 〖F:docs/guides/subagents.md†L64-L76〗

Open Question
- Do we implement a small parser that maps YAML limit specs to Inspect `Limit` objects and return them from `load_and_build`, or do we remove the field to avoid confusion and keep limits strictly at the Python callsite/runner?

Options
- A) Implement parser now (time/message/token) and return `limits` from `load_and_build` so callers can pass them to `run_agent`.
- B) Remove/ignore the field and document runner‑level responsibility only.

Recommendation (pending)
- A) Implement a minimal parser for the three core limit types; keep behavior optional and backward compatible.

Decision Needed
- Choose A or B; if A, define the minimal schema. Target: 2025‑09‑12.

---

# Retries & Cache — Per‑Agent Env in v1 or Global Only? (New)

Context
- The guidance proposes env‑first configuration with per‑agent overrides (`...__<AGENT_NAME>` suffix), but the code does not yet plumb retries/cache through `build_supervisor/build_subagents`. 〖F:docs/guides/retries_cache.md†L58-L94〗

Open Question
- For the first release, should we support per‑agent env overrides, or keep a single global env (simpler) and add per‑agent later?

Options
- A) Global only in v1 (`INSPECT_AGENTS_CACHE`, `INSPECT_AGENTS_MAX_RETRIES`, `INSPECT_AGENTS_TIMEOUT_S`).
- B) Global + per‑agent suffix in v1 (consistent with quarantine filters).

Recommendation (pending)
- A) Start global to reduce scope; add per‑agent once APIs are in place.

Decision Needed
- Choose A or B. Target: 2025‑09‑12.

---

# Sandbox Preflight & `text_editor` Exposure (New)

Context
- FS tools proxy to `text_editor`/`bash_session` in sandbox mode. We cache a preflight result; exposure of `text_editor()` in `standard_tools()` is env‑gated but not preflight‑aware.

Problem
- Exposing `text_editor()` when sandbox is unavailable leads to confusing failures. We need a best‑effort sync check without making `standard_tools()` async.

Options
- Option A — Best‑effort gating: expose only when stubs are present in‑process or a strict env hint is set (e.g., `INSPECT_SANDBOX_PREFLIGHT=force`).
- Option B — Always expose when env flag is set; rely on tool‑path preflight and fallback messaging.
- Option C — New mode flags: `auto|force|skip` that affect both exposure and tool‑path behavior; include a `reset` API and optional TTL recheck.

Recommendation (pending)
- Adopt A for immediate UX improvement; stage C (modes + reset + TTL) as follow‑ups.

Decision Needed
- Approve gating semantics and env names: `INSPECT_SANDBOX_PREFLIGHT=auto|force|skip`, `INSPECT_SANDBOX_PREFLIGHT_TTL=<sec>`. Target: 2025‑09‑11.

---

# Model Roles — Strict Mode & Unmapped Warnings (New)

Context
- `resolve_model()` supports role mapping via env. Some deployments want stricter behavior (fail fast on unmapped roles) and better diagnostics.

Problem
- Typos or missing mappings silently fall back to `inspect/<role>`; harder to catch in CI.

Options
- Option A — Add `INSPECT_ROLES_STRICT=1` to raise on unmapped roles; optional allowlist.
- Option B — Add `INSPECT_ROLES_WARN_UNMAPPED=1` to log a warning once per role when falling back.
- Option C — Support repo defaults via `pyproject.toml` to reduce reliance on env.

Recommendation (pending)
- Implement A+B; consider C later (cached `tomllib` read) to keep hot path light.

Decision Needed
- Approve strict/warn flags and allowlist format. Target: 2025‑09‑15.

---

# Tool Output Truncation — Defaults, Env Override, Counts Line (New)

Context
- ADR 0004 proposes formalizing a 16 KiB default for tool output truncation, plus an optional env override and a counts line outside the payload envelope.

Problem
- Today the default is implied by a fallback; users can’t change it fleet‑wide without code changes; it’s unclear how much was truncated.

Options
- Option A — Set `GenerateConfig.max_tool_output = 16*1024` by default (upstream), keep function fallback.
- Option B — Add env `INSPECT_MAX_TOOL_OUTPUT` (low precedence) read by `truncate_tool_output` when config is None.
- Option C — Add a counts line above `<START_TOOL_OUTPUT>` stating shown vs original bytes.

Recommendation (pending)
- Adopt A+B+C; keep precedence `arg > config > env > fallback` and add one‑time log when env is used.

Decision Needed
- Approve upstream change and env name; confirm counts line copy. Target: 2025‑09‑13.

---

# Docs Synchronization — Limits & FS Behavior (New)

Context
- Some tool docs drifted from code (e.g., byte ceilings in write/edit and sandbox path validation).

Problem
- Readers may be misled about safety limits and validation; drift accumulates without checks.

Options
- Option A — Add a lightweight docs check that greps for key claims (size caps, delete policy) in tool pages and compares against code constants/envs.
- Option B — Consolidate canonical defaults in a single page (already `docs/tools/_defaults.md`) and keep tool pages thin; avoid duplicating limits.

Recommendation (pending)
- Prefer B; add a CI reminder to update `_defaults.md` when touching relevant code paths.

Decision Needed
- Approve policy and CI reminder location. Target: 2025‑09‑10.

---

# Approvals Presets — Include Handoff Exclusivity by Default? (New)

Context
- Presets `ci|dev|prod` are implemented; a separate `handoff_exclusive_policy()` enforces “first handoff wins” at approval‑policy level (v1). These are currently independent. 〖F:src/inspect_agents/approval.py†L126-L183〗 〖F:src/inspect_agents/approval.py†L195-L216〗

Open Question
- Should `approval_preset("dev")` and `approval_preset("prod")` include `handoff_exclusive_policy()` by default so users get exclusivity out‑of‑the‑box?

Options
- A) Yes — add the exclusivity policy to `dev` and `prod` presets; `ci` remains approve‑all.
- B) No — keep it separate; document combinators in the approvals guide.

Recommendation (pending)
- A) Yes — makes handoffs safer by default; aligns with ADR 0005 behavior and expectations.

Decision Needed
- Choose A or B; if A, update the approvals guide/preset docs. Target: 2025‑09‑08.

# Docs — Built-in Tools List (Dedup + Canonicalization)

Context
- On 2025-09-03 we de-duplicated the Built-in tools list in `docs/tools/README.md`, promoting `files` as the canonical unified entry and listing legacy wrappers (`ls`, `read_file`, `write_file`, `edit_file`, `delete_file`) once, labeled as wrappers. This reduces drift and points users to a single source of truth.
- The unified `files` tool exposes a discriminated union of commands (`ls`, `read`, `write`, `edit`, `delete`) and serves as the API contract; wrappers exist for compatibility and ergonomics. See `docs/tools/files.md` for command model and result schemas.

## 1) Where should the “Parallelism/Exclusivity” story live?

Problem
- Concurrency semantics for file operations are not documented in a single, authoritative place. Questions include: whether file ops are serialized globally or per-path; whether reads can proceed in parallel; whether writes/edits are exclusive; and how behavior differs between `store` and `sandbox` modes (e.g., deletes disabled in sandbox).

Options
- Option A — Centralize: Add a “Concurrency & Exclusivity” section to `docs/tools/files.md` as the canonical reference. In `docs/tools/README.md`, include a one-line note beneath the `files` bullet that links to the canonical section. Wrapper pages state “inherits `files` concurrency semantics” and link back.
- Option B — Per-tool pages: Document concurrency on every wrapper page and in the README. Pros: local discoverability; Cons: duplication and drift risk.
- Option C — Hybrid: Canonical section in `files.md` plus a short “inherits semantics” line in wrapper pages; README carries only a compact pointer to the canonical section.

Considerations
- Keep statements strictly to known invariants (timeouts, limits, mode differences) and avoid implying implementation details not guaranteed by the API contract. If behavior is implementation-defined, state it explicitly and advise user-level serialization for conflicting writes.

Recommendation
- Favor Option C: one canonical section in `files.md` with minimal, link-back notes elsewhere. This minimizes drift while keeping users oriented.

Decision Needed
- Choose A/B/C and authorize adding/linking the canonical section. Owner: Docs. Target: before next docs publish.

References
- `docs/tools/README.md` (Built-in list) and `docs/tools/files.md` (unified commands, FS modes, limits).

## 2) Preferred ordering for non-file built-ins

Problem
- After normalization, the Built-in list leads with `files` and then its wrappers; `write_todos`/`update_todo_status` follow. We need a style rule to keep ordering consistent going forward.

Options
- Option A — Canonical-first: `files` first, then its wrappers alphabetically, then all other built-ins alphabetically (TODO tools included).
- Option B — Fully alphabetical: Sort all Built-in tools alphabetically, including `files` and wrappers.
- Option C — Grouped: Use subgroups under Built-in (e.g., “File Operations”, “Task/Todos”), each sorted alphabetically.

Considerations
- Canonical-first emphasizes the source of truth; Alphabetical is easiest to maintain; Grouped conveys mental model at the cost of structure sprawl in a short README section.

Recommendation
- Option A for simplicity and emphasis, unless the list grows substantially, in which case Option C becomes attractive.

Decision Needed
- Pick A/B/C and add the rule to the docs style guide. Owner: Docs.

## 3) Should wrapper bullets name exact `files` mappings?

Problem
- The README currently labels wrappers generically as “wrapper over `files`”. It may aid clarity to state the explicit mapping to the unified `files` command discriminator (e.g., `command: "read"`).

Options
- Option A — Name mappings inline in README: e.g., “read_file — wrapper over `files` (`command: read`)”.
- Option B — Keep README generic; document precise mappings on each wrapper page’s Overview, and maintain a single authoritative mapping table in `files.md`.
- Option C — Add a small mapping table to `files.md` only and link to it from README and wrapper pages.

Considerations
- Inline mappings improve immediacy but can drift; a central table reduces drift but adds a click. Ensure terminology matches the canonical API (discriminant `command` with values `ls|read|write|edit|delete`).

Recommendation
- Option C: a single mapping table in `files.md` referenced from README and wrappers, with wrapper pages stating “inherits semantics; maps to `command: <x>`”.

Decision Needed
- Choose A/B/C and update README + wrapper pages accordingly. Owner: Docs.


---

# Open Questions — ADR 0004: Filesystem Sandbox Guardrails

Last updated: 2025-09-03

Scope: Tracks outstanding decisions related to ADR 0004’s hardening plan. ADR is “Accepted, partially implemented”; code implements sandbox routing, root confinement, symlink denial, byte ceilings, and timeouts. Future work includes atomic rename and a read‑only mode.

References:
- ADR 0004: docs/adr/0004-filesystem-sandbox-guardrails.md
- Mode helpers: src/inspect_agents/tools_files.py (`_use_sandbox_fs`, `_max_bytes`, `_validate_sandbox_path`, `_deny_symlink`), src/inspect_agents/tools.py (`_fs_mode`)
- Sandbox ops: src/inspect_agents/tools_files.py (`execute_ls`, `execute_read`, `execute_write`, `execute_edit`)
- Env template default: env_templates/inspect.env (INSPECT_AGENTS_FS_MODE)
- Tests: tests/unit/inspect_agents/test_fs_root_confinement.py, tests/unit/inspect_agents/test_symlink_preflight.py, tests/unit/inspect_agents/test_files_tool_unified.py

---

## 1) Read‑only mode flag for sandbox FS

- Problem: ADR calls for a read‑only mode to support audit workflows. Today, sandbox mode allows read/write/edit (delete disabled). We need a flag and enforcement points to block writes/edits while keeping `ls`/`read` available on host FS.
- Options:
  - Option A (recommended): `INSPECT_AGENTS_FS_READ_ONLY=1`. Enforce in `execute_write`, `execute_edit`, `execute_delete` (src/inspect_agents/tools_files.py). If set and sandbox active, raise a ToolException; allow `ls`/`read`. Store mode unaffected.
  - Option B: Extend `INSPECT_AGENTS_FS_MODE` with `readonly` or `ro`. Requires touching `_fs_mode()`/`_use_sandbox_fs()` and all mode conditionals; higher blast radius.
  - Option C: Add per‑call `read_only` param with env default. More flexible but expands tool surface/validation.
- Recommendation: Option A now; consider C later if needed.
- Decision Needed: Confirm env name and scope (sandbox‑only vs global).

---

## 2) Promote root confinement + symlink denial to Baseline

- Problem: ADR currently lists these under “Recommended Guardrails,” but code enforces them in sandbox flows before editor calls, creating a doc/behavior mismatch.
- Options:
  - Option A (recommended): Move both to “Security Baseline (documented behavior today)” with a note that they apply in sandbox mode and are bypassed when falling back to Store.
  - Option B: Keep under “Recommended Guardrails” and clarify in Implementation Status that they are implemented.
- Recommendation: Option A for clarity with current behavior.
- Decision Needed: Approve ADR edits to promote to Baseline with clarifying language.

---

## 3) Include explicit test pointers in ADR 0004

- Problem: ADRs benefit from traceability; adding test file pointers aids reviewers and maintainers.
- Options:
  - Option A (recommended): Under “Rollout & Testing,” add a “Verification Artifacts” list with: test_fs_root_confinement.py, test_symlink_preflight.py, test_files_tool_unified.py.
  - Option B: Keep ADR free of test refs; document them only in reference docs.
- Recommendation: Option A; keep the list short to reduce maintenance.
- Decision Needed: Include explicit test pointers in ADR 0004?

---

## 4) Additional future work beyond atomic rename and read‑only

- Problem: Decide if adjacent hardening items should be added to ADR 0004 now or tracked in backlog docs.
- Candidates:
  - Safer edits: `expected_count` + `dry_run` for `str_replace` (store enforcement + sandbox pre‑read).
  - Path policy: optional allowlist regex (e.g., `INSPECT_AGENTS_FS_ALLOW_RE`) to complement FS root.
  - Telemetry: one‑time warning when sandbox transport is unavailable and we fall back to Store.
  - Time/scan budgets: optional per‑op limits for `read`/`ls` on host FS.
- Recommendation: Add `expected_count + dry_run` to ADR 0004 Future Work now; track others in backlog.
- Decision Needed: Which items (if any) to promote into ADR 0004?

---

## Observability Hygiene — Tool Event Logging

Context
- Files and other tools should never log raw payloads in `tool_event` arguments. We tightened call-site logging for file operations (e.g., `files:write` emits `{file_path, content_len, instance}`), and added a shared defensive guard to `_log_tool_event` to prevent accidental leakage from future callers.

### 1) Test enablement for logging hygiene

Problem
- Async tests rely on `pytest-asyncio`/`anyio`. Some environments block network installs, hindering local verification.

Options
- Option A (preferred): use `uv` to resolve and run the targeted tests with CI-like flags.
  - Resolve: `uv sync`
  - Run: `CI=1 NO_NETWORK=1 PYTHONPATH=src:external/inspect_ai uv run pytest -q tests/inspect_agents/test_tool_observability.py`
- Option C (fallback): add a temporary smoke test that drives `files:read/write/edit` via asyncio and asserts `tool_event.args` contains only `*_len` fields and never raw `content|file_text|old_string|new_string`. Remove once CI is reliable locally.

Decision Needed
- Choose A or C to ensure we can attach evidence for PRs touching observability.

### 2) Defensive guard inside `_log_tool_event` (DECIDED — 2025‑09‑03) — DONE

Decision
- Implement a lightweight normalization inside `_log_tool_event` to rewrite sensitive keys to length-only metadata before redaction/truncation.

Implementation Summary
- Mapping (allowlist): `content→content_len`, `file_text→file_text_len`, `old_string→old_len`, `new_string→new_len`.
- Remove original raw fields before passing to `_redact_and_truncate`. Apply only to `args` (not `extra`). On error, fall back to original `args` and still apply redaction/truncation.

Follow-ups
- Add a unit test that feeds raw fields into `_log_tool_event` and asserts only `*_len` remain.
- Decide whether to normalize `extra` similarly; if so, use the same allowlist and document it.
- Consider expanding the allowlist for future fields like `diff_text`, `patch`, `blob`, `stdout`, `stderr`.

<details>
<summary><strong>Answer</strong></summary>

- Implemented in code: `_log_tool_event` rewrites sensitive argument fields to length-only metadata before redaction/truncation, ensuring no raw `content|file_text|old_string|new_string` values are logged. 〖F:src/inspect_agents/tools.py†L98-L120〗
- Callers updated to pass length metadata:
  - `files:write` logs `content_len` instead of raw `content`. 〖F:src/inspect_agents/tools_files.py†L642-L646〗
  - `files:edit` logs `old_len`/`new_len` instead of raw strings. 〖F:src/inspect_agents/tools_files.py†L719-L729〗
- Outcome: tool-event payloads contain only sizes for sensitive fields; original raw strings are removed prior to redaction/truncation, aligning with the observability guidance in ADR 0005. 〖F:docs/adr/0005-tool-parallelism-policy.md†L16-L25〗

</details>

### 3) Repository‑wide regression guard

Problem
- Future code could reintroduce raw content into `tool_event` payloads.

Option
- Add a caplog-based unit test that fails when:
  - Sensitive keys appear with string values (`content`, `file_text`, `old_string`, `new_string`).
  - Any string in `args` (optionally `extra`) exceeds a conservative length threshold (e.g., >512 chars).

Recommendation
- Include a single, fast unit test in `tests/inspect_agents/` that exercises `files:read/write/edit` and scans captured records. Keep deterministic and offline by default.

Decision Needed
- Should this guard be part of the default test run?

Notes
- Scope limited to observability payloads; functional returns unchanged. Redaction/truncation remains a final backstop.

## 2) Unifying transcript “skip” events across v1 (policy) and v2 (executor)

- Today in v1: Rejected calls carry `Approval(decision="reject", explanation="Skipped due to handoff exclusivity")` and we log a local event via `_log_tool_event(name="handoff_exclusive", phase="skipped", ...)`. 〖F:src/inspect_agents/approval.py†L262-L279〗

- Goal: Ensure transcripts present a consistent “skip” artifact regardless of where exclusivity is enforced (policy vs executor), without polluting conversation history. ADR recommends ToolEvents for skipped calls and no conversation messages. 〖F:docs/adr/0005-tool-parallelism-policy.md†L22-L25〗

- Proposed shape (both v1 and v2):
  - `type: tool_event`, `pending: false`
  - `error.code: "skipped"`, `error.message: "Skipped due to handoff"`
  - `meta.selected_handoff_id: <id>`, `meta.skipped_function: <name>`
  - `meta.source: "policy/handoff_exclusive" | "executor/prescan"`

- Implementation notes:
  - v1: In addition to Approval rejection, mint a standardized ToolEvent so transcripts match v2. Keep `_log_tool_event` for local logs/metrics. 〖F:src/inspect_agents/approval.py†L265-L274〗
  - v2: When pre‑scan skips enqueuing, synthesize the same ToolEvent at the executor boundary. 〖F:docs/adr/0005-tool-parallelism-policy.md†L53-L55〗

- Validation: Tests should assert presence of a single handoff result, absence of extra conversation messages, and N "skipped" ToolEvents with consistent shape. 〖F:docs/adr/0005-tool-parallelism-policy.md†L70-L75〗

Decision needed by: 2025‑09‑10.

---

## 3) Environments that must retain serial‑only execution beyond `INSPECT_DISABLE_TOOL_PARALLEL=1`

- Current control: `INSPECT_DISABLE_TOOL_PARALLEL=1` forces serial execution of non‑handoff tools; handoff exclusivity still applies via v1 policy (and v2 if enabled). 〖F:docs/adr/0005-tool-parallelism-policy.md†L29-L31〗 〖F:docs/adr/0005-tool-parallelism-policy.md†L49-L56〗

- Candidate environments requiring serial‑only:
  - Regulated or audited workflows where tool ordering must reflect user‑visible chronology.
  - Interactive demos/debug sessions where interleaving logs obscure reasoning.
  - Backends with global process‑wide state or side‑effects not yet isolated by tools.

- Guidance:
  - Keep `INSPECT_DISABLE_TOOL_PARALLEL=1` as the single control for serialism; it is orthogonal to handoff exclusivity (gating) which remains enforced in both v1 and v2.

---

# Open Questions — Inspect Research Example Migration

This page tracks open decisions that surfaced while migrating the Research example to the Inspect‑AI path (Features 1–8). Each item includes context, current behavior, options, and a lightweight recommendation to help converge quickly.

## 1) Web‑Search UX: CLI flags vs env‑only
- Context: Feature 2/3 added sub‑agents and switched to Inspect `web_search`. We exposed a minimal `--enable-web-search` flag, while other toggles remain env‑driven.
- Current Behavior: `examples/research/run_local.py` supports `--enable-web-search` (sets `INSPECT_ENABLE_WEB_SEARCH=1`), other toggles (exec, browser, text editor) are env‑only.
- Options:
  - A) Keep only `--enable-web-search`; leave other toggles to env (simple CLI).
  - B) Add parity flags (`--enable-exec`, `--enable-web-browser`, `--enable-text-editor-tool`) mirroring `examples/inspect/run.py`.
- Considerations: simplicity vs. parity; support burden; discoverability of power features.
- Tentative Recommendation: Start with A (current), revisit parity after first user feedback.

## 2) Supervisor Prompt Guidance for Handoffs
- Context: Feature 2 introduced `transfer_to_<name>` tools. Prompt could nudge delegation explicitly.
- Current Behavior: Simple prompt "You are a helpful researcher." (inline path) or YAML prompt in `examples/research/inspect.yaml`.
- Options:
  - A) Keep minimal; rely on tool descriptions.
  - B) Add a short guidance block encouraging use of `transfer_to_research-agent` and `transfer_to_critique-agent`.
- Considerations: Too much specificity may overfit; minimal works with most models.
- Tentative Recommendation: B, add a one‑sentence nudge once sub‑agent prompts settle.

## 3) Quarantine Convenience Flag
- Context: Quarantine is env‑controlled (`INSPECT_QUARANTINE_MODE`, `INSPECT_QUARANTINE_INHERIT`).
- Current Behavior: Documented in runner help epilog; no CLI flag.
- Options:
  - A) Add `--quarantine-mode strict|scoped|off` to export env before build.
  - B) Keep env‑only to avoid CLI sprawl.
- Considerations: Tests/docs already reference env; flag is sugar.
- Tentative Recommendation: A (small, non‑breaking UX improvement).

## 4) Handoff Exclusivity in CI
- Context: Feature 4 appends `handoff_exclusive_policy()` for dev/prod approvals presets.
- Current Behavior: Applied for `--approval dev|prod`, not for `ci`.
- Options:
  - A) Apply in CI too (ensures deterministic single‑handoff behavior in automation).
  - B) Leave CI permissive (fast, fewer rejections).
- Considerations: CI flakes vs. debugging friction.
- Tentative Recommendation: A, enable in CI as well.

## 5) Top‑Level README Callout
- Context: Research example is now Inspect‑native.
- Current Behavior: No explicit snippet in the repo root README.
- Options:
  - A) Add a short "Research Example" run command (with link to docs page).
  - B) Rely on MkDocs navigation only.
- Considerations: Many readers scan the README first.
- Tentative Recommendation: A, add a 3‑line snippet.

## 6) Makefile Convenience Target
- Context: Users often benefit from a one‑shot target for examples.
- Current Behavior: No Makefile target.
- Options:
  - A) Add `make research` → `uv run python examples/research/run_local.py "..."`.
  - B) Skip to avoid Makefile drift.
- Considerations: Optional; low cost.
- Tentative Recommendation: A, add minimal target with overridable `PROMPT`.

## 7) Test That Triggers a Handoff
- Context: Feature 6 smoke test uses a toy submit model; it doesn’t exercise `handoff()` end‑to‑end.
- Current Behavior: New test asserts completion + transcript only.
- Options:
  - A) Add a toy model that first calls `transfer_to_research-agent`, then `submit` (assert quarantine filtering via store keys).
  - B) Keep current minimal smoke.
- Considerations: Extra coverage for filters; modest complexity.
- Tentative Recommendation: A, add a second test.

## 8) Transcript Directory Policy in Tests
- Context: Feature 6 writes transcripts to `tmp_path` via `INSPECT_LOG_DIR`.
- Current Behavior: Always sets a temp dir in the test.
- Options:
  - A) Keep forcing temp dir (hermetic).
  - B) Use default `.inspect/logs` (matches docs).
- Considerations: Hermetic tests preferred.
- Tentative Recommendation: A (keep hermetic).

## 9) Docs Depth: "Handoffs in Action" and Troubleshooting
- Context: Feature 7 adds a Getting Started page for the example.
- Current Behavior: No explicit handoff transcript walkthrough; troubleshooting is brief.
- Options:
  - A) Add a short transcript excerpt showing a `transfer_to_research-agent` call and outcomes.
  - B) Add a Troubleshooting box (missing Ollama/LM‑Studio; provider envs; transcript path).
  - C) Keep minimal.
- Considerations: Support burden vs. page length.
- Tentative Recommendation: A+B in a collapsible details block.

## 10) YAML Approvals Example
- Context: Feature 8 adds `inspect.yaml` but no approvals block.
- Current Behavior: Presets are passed via `--approval`; YAML left empty for simplicity.
- Options:
  - A) Include a commented example that gates `bash`/`python`.
  - B) Provide a separate `inspect.approvals.yaml` sample.
  - C) Leave as‑is.
- Considerations: Avoid confusion between CLI presets and inline rules.
- Tentative Recommendation: A (commented example inline).

## 11) Provider/Model Flags Parity
- Context: Runner currently relies on resolver defaults; the Inspect example runner exposes `--provider/--model`.
- Current Behavior: No provider/model flags in `examples/research/run_local.py`.
- Options:
  - A) Add `--provider` and `--model` (pass to `resolve_model`).
  - B) Keep implicit/local‑first.
- Considerations: Parity vs. simplicity; many users appreciate explicit control.
- Tentative Recommendation: A, add flags mirroring `examples/inspect/run.py`.

---

Owner: Inspect‑AI migration maintainers  
Last updated: YYYY‑MM‑DD  
Status: Open — accepting comments and PRs.
  - If both `INSPECT_DISABLE_TOOL_PARALLEL=1` and `INSPECT_EXECUTOR_PRESCAN_HANDOFF=1` are set: executor runs serially and also pre‑scans to avoid enqueuing skipped calls; transcript should still include standardized "skipped" ToolEvents as above.
  - For stricter governance, pair with an approval preset that gates broad tool usage (e.g., prod gate). 〖F:src/inspect_agents/approval.py†L180-L189〗

- Open point: Document explicit precedence rules (serial vs pre‑scan are orthogonal; neither overrides the other). Confirm this in executor docs when v2 lands.

Decision needed by: 2025‑09‑10.

---

# Eval Logs — read_log_eval.py Enhancements (Open Questions)

Last updated: 2025-09-03

Context
- We updated `scripts/read_log_eval.py` to load environment variables from `.env` and optional `INSPECT_ENV_FILE`, resolve `INSPECT_LOG_DIR` (defaulting to `.inspect/logs`), locate the newest `*.eval` file, and analyze it using `inspect_ai.analysis` (evals/samples/messages/events). It prints DataFrame heads and writes four CSVs in the current working directory. 〖F:scripts/read_log_eval.py†L29-L46〗 〖F:scripts/read_log_eval.py†L71-L76〗 〖F:scripts/read_log_eval.py†L79-L88〗 〖F:scripts/read_log_eval.py†L91-L113〗 〖F:.env†L46-L47〗
- The script exposes `--list` and `--file` for log discovery/selection. 〖F:scripts/read_log_eval.py†L117-L120〗

Goals
- Clarify desired outputs and defaults to make the script useful for both quick inspection and downstream analysis.

## 1) Additional summary statistics and health signals

Problem
- Current output shows only `.head()` previews for each DataFrame and writes raw CSV dumps. There is no at‑a‑glance summary of pass/fail counts, error rates, or timing distributions.

Options
- Console summary: compute and print simple aggregates (e.g., sample count, unique tasks, basic score distribution if a score column exists, number of error events). Keep O(1) printing and guard column references. 
- Summary artifact: write a `summary.json` and/or `summary.csv` containing the aggregates for programmatic consumption.
- Toggle: add `--summary` (default on) to enable aggregates; `--no-summary` to suppress.

Considerations
- Column names vary by eval/task; code must check for presence before aggregating to avoid brittle assumptions.

Recommendation (pending)
- Add a lightweight console summary and a small `summary.json` with a fixed schema (`counts`, `columns_present`, `notes`).

Decision Needed
- Approve adding summary computation with default on; confirm minimal schema (target: 2025‑09‑06).

## 2) Where to write the CSV (output location)

Problem
- CSVs are written to the current working directory, which can scatter artifacts across repos or terminals and mix outputs from different logs. 〖F:scripts/read_log_eval.py†L108-L113〗

Options
- CWD (status quo): simplest, no extra flags; least organized.
- Sidecar (near log): write next to the `.eval` file (e.g., `.inspect/logs/<log>.{csv}`), keeping artifacts co‑located with the source.
- Configurable out‑dir: add `--out-dir <path>` (and ENV `INSPECT_EVAL_OUT_DIR`) with special value `same` to place outputs beside the log.

Recommendation (pending)
- Add `--out-dir` (default `.`). If set to `same`, write sidecar files next to the log. Keep behavior explicit to avoid unexpected writes inside `.inspect/logs`.

Decision Needed
- Choose default: `.` vs `same`. Approve the `--out-dir` flag (target: 2025‑09‑06).

## 3) Export formats beyond CSV (JSONL / Parquet)

Problem
- Nested fields in events/messages can be lossy in CSV; consumers often prefer line‑delimited JSONL or columnar Parquet for analytics.

Options
- JSONL: add `--format jsonl` using `DataFrame.to_json(lines=True, orient="records")` per table.
- Parquet: add `--format parquet` behind an optional dependency (pyarrow/fastparquet) with graceful fallback if missing.
- Multi‑format: allow comma‑separated `--format csv,jsonl` to emit multiple artifacts.

Recommendation (pending)
- Support `jsonl` first (no new deps). Gate `parquet` behind optional install; emit a clear message if unavailable.

Decision Needed
- Approve `jsonl` and optional `parquet` support (target: 2025‑09‑06).

## 4) Log selection filters (timestamp range, name prefix)

Problem
- Selection is either explicit `--file` or the single latest file. There is no way to target a day/range or restrict by name prefix. 〖F:scripts/read_log_eval.py†L79-L88〗 〖F:scripts/read_log_eval.py†L145-L147〗

Options
- Time filters: `--since 2025-09-03T00:00`, `--until 2025-09-03T23:59` (compare mtime).
- Name filters: `--prefix 2025-09-03T` to narrow by date prefix or task name.
- Listing controls: `--limit N` to cap the `--list` output for large directories.

Recommendation (pending)
- Add `--since`, `--prefix`, and `--limit` first; consider `--until` later if needed.

Decision Needed
- Approve filter flags and defaults (target: 2025‑09‑06).

Notes
- The script already respects `INSPECT_ENV_FILE` and `.env` without overriding process env and resolves `INSPECT_LOG_DIR` correctly; changes above should not alter those invariants. 〖F:scripts/read_log_eval.py†L29-L46〗 〖F:scripts/read_log_eval.py†L71-L76〗

---

# API Unification and Exports — Public Surface and Naming (New)

Last updated: 2025‑09‑04

Context
- Goal: present a coherent public API for agent builders under a single import path for discoverability, while retaining backward compatibility.
- Current code:
  - Root exports now re‑export builders from the unified agents surface. 〖F:src/inspect_agents/__init__.py†L4-L17〗
  - Unified surface `inspect_agents.agents` exposes `build_supervisor` (submit style), a parity alias `build_basic_submit_agent`, and `build_iterative_agent` (no submit). 〖F:src/inspect_agents/agents.py†L96-L138〗 〖F:src/inspect_agents/agents.py†L142-L170〗 〖F:src/inspect_agents/agents.py†L141-L152〗 〖F:src/inspect_agents/agents.py†L161-L170〗
  - Examples/docs are being updated to import builders from `inspect_agents.agents`. 〖F:examples/research/run_iterative.py†L22-L32〗 〖F:docs/todo_paperbench_iterative_agent.md†L30-L37〗

Open Questions
1) Preferred import style in docs and examples
   - Options: (A) Standardize on `from inspect_agents.agents import ...` for all builders; (B) Keep mixed style (root import for convenience, agents for clarity); (C) Root import only.
   - Considerations: discoverability, auto‑complete affordances, alignment with submodule structure.
   - Recommendation (pending): (A) Prefer `inspect_agents.agents` in new docs/examples; keep root re‑exports for BC.

2) Naming of the submit‑style builder
   - Problem: We introduced `build_basic_submit_agent` as an alias for `build_supervisor` to present paired names alongside `build_iterative_agent`. Should we keep both, or converge on one canonical name in docs?
   - Options: (A) Keep both; docs prefer `build_basic_submit_agent` in side‑by‑side comparisons; (B) Prefer `build_supervisor` in docs and omit the alias from public docs; (C) Deprecate the alias later.
   - Recommendation (pending): (B) Keep alias for parity but prefer `build_supervisor` in docs to avoid naming sprawl. 〖F:src/inspect_agents/agents.py†L142-L170〗

3) Root exports policy and deprecation window
   - Problem: Root `__init__` re‑exports builders for convenience. Do we want to document a future deprecation of builder exports at the root to simplify the top‑level namespace?
   - Options: (A) Keep root exports indefinitely; (B) Mark as “convenience re‑exports” with no deprecation; (C) Announce an optional migration path with a future major release toggle.
   - Recommendation (pending): (A) Keep indefinitely; this is low‑cost and avoids churn. 〖F:src/inspect_agents/__init__.py†L4-L17〗

4) Linter/docs guardrails
   - Question: Should we add a docs check that flags new snippets importing builders from the root instead of `inspect_agents.agents`, to keep the style consistent?
   - Option: Add a lightweight docs lint in CI that greps for `from inspect_agents import build_` in `docs/` (allow‑listed exclusions permitted).

Decision Needed
- Choose preferred import style and naming guidance for submit vs iterative builders; define CI/docs lint scope (if any). Target: 2025‑09‑08.

---

# Iterative Agent (No Submit) — Open Questions (New)

Last updated: 2025‑09‑04

Context
- Implemented `build_iterative_agent`: ephemeral “continue” nudge added to a copy of history each step; assistant/tool results persist; loop bounded by time and step limits.  Safe default toolset (Files/Todos built‑ins; exec/search/browser via env). 〖F:src/inspect_agents/iterative.py†L62-L74〗 〖F:src/inspect_agents/iterative.py†L130-L168〗
- Examples: CLI runner and Inspect task variant under `examples/research/`. 〖F:examples/research/run_iterative.py†L41-L63〗 〖F:examples/research/iterative_task.py†L27-L41〗

Questions
1) Code‑only variant toggle
   - Problem: Some workflows prefer “code‑only” prompting (bias toward file ops; avoid execution). Should the builder expose `code_only: bool` that adjusts the default system message and hides exec tools unless explicitly enabled?
   - Options: (A) Add builder flag; (B) rely on user‑supplied `prompt`; (C) environment variable `INSPECT_CODE_ONLY`.
   - Recommendation (pending): (A) explicit flag for clarity; env as secondary.

2) Default toolset baseline
   - Problem: Keep the iterative agent minimal (Files/Todos) vs auto‑include `think()` and/or `web_search()` when configured.
   - Options: (A) keep minimal (status quo); (B) always include `think()`; (C) include `web_search` when keys present.
   - Trade‑offs: action‑space breadth vs determinism/cost.
   - Recommendation (pending): (A) minimal; document opt‑ins. 〖F:src/inspect_agents/tools.py†L206-L229〗

3) Optional submit/end tool
   - Problem: Some flows want an explicit “done” signal without scoring. Add optional submit tool that simply terminates?
   - Options: (A) keep pure time/step termination; (B) gate a no‑op submit behind a flag; (C) recommend the submit‑style supervisor instead.
   - Recommendation (pending): (C) recommend supervisor; revisit if demand emerges.

4) Default limits and env fallbacks
   - Problem: Examples default to `600s/40 steps`; no repo‑level env standard.
   - Options: (A) explicit args only; (B) add `INSPECT_ITERATIVE_TIME_LIMIT` / `INSPECT_ITERATIVE_MAX_STEPS`; (C) runners convert YAML limit specs to Inspect `Limit`s.
   - Recommendation (pending): (B) add env fallbacks while keeping explicit args. 〖F:examples/research/run_iterative.py†L47-L53〗 〖F:examples/research/iterative_task.py†L31-L41〗

5) Progress ping cadence
   - Problem: Pings every 5 steps aid visibility but add tokens/logs.
   - Options: (A) fixed cadence; (B) `progress_every` parameter where 0 disables; (C) suppress in tasks by default.
   - Recommendation (pending): (B) parameterize; default 5.

6) Context management (pruning vs summarization)
   - Problem: Current loop only reacts to length overflow and nudges to summarize; no active pruning.
   - Options: (A) sliding‑window pruning; (B) summarization of older chunks into a system note; (C) hybrid.
   - Recommendation (pending): (A) add a small sliding window; consider (B) later.

7) Retry/backoff observability
   - Problem: PaperBench measured provider backoff time; we rely on Inspect telemetry.
   - Options: (A) status quo; (B) add a generate wrapper to record backoff counters in transcript; (C) structured log counters.
   - Recommendation (pending): (A) for now; revisit if gaps appear in logs/traces.

8) Sub‑agent handoff support
   - Problem: Should the iterative agent support handoff to sub‑agents or remain single‑agent?
   - Options: (A) single‑agent (status quo); (B) optional handoff tool; (C) use the supervisor composition when handoff is needed.
   - Recommendation (pending): (C) prefer supervisor for orchestration.

9) Iterative task flags for web search
   - Problem: `iterative_task.py` exposes `enable_exec` only.
   - Options: (A) add `enable_web_search: bool`; (B) keep env‑only; (C) separate research‑oriented iterative task.
   - Recommendation (pending): (A) add a boolean flag for parity with runner.

10) YAML composition for iterative
   - Problem: Research YAML targets supervisor/subagents; none for iterative.
   - Options: (A) Python‑only; (B) extend YAML with an `iterative` section; (C) `supervisor.mode: iterative` variant.
   - Recommendation (pending): (A) for now; reassess with usage.

Decision Needed
- Prioritize (1), (5), (6), (9) for next release; confirm toolset policy (2). Target: 2025‑09‑15.

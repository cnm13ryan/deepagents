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

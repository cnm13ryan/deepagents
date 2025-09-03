# DECISIONS-PENDING — Inspect-AI Rewrite vs deepagents (LangGraph/LangChain)

Purpose
- Track behavioral deviations between the existing deepagents framework and the Inspect‑AI–native rewrite.
- For each area: enumerate behaviors, options, proposed defaults, user/test impact, and migration plan.
- Until finalized, guard non‑parity behaviors behind a single feature flag: `parity_mode` (true = mimic deepagents; false = Inspect‑native).

Status & Process
- Status values: Pending | Tentative | Decided.
- Any “Tentative” default may ship behind `parity_mode=false`; flip to “Decided” after examples + tests are green.
- Owners should link PRs and update “Test Impact” and “Migration Plan”.

Legend
- deepagents = current LangGraph/LangChain implementation under `src/deepagents/*`.
- Inspect-native = new modules under `src/inspect_agents/*` (rewrite).

---

ID D1 — State Model & Persistence
- Behavior (deepagents): `AgentState` with `todos: list[Todo]` and in‑memory `files: dict[path,str]`; merged via reducer; ephemeral per run.
- Behavior (Inspect-native): `Store`/`StoreModel` for `Todos` and `Files`, optionally instance‑scoped per agent; persisted and transcripted.
- Options:
  1) Parity only: keep ephemeral in‑memory store semantics (no cross‑run persistence).
  2) Inspect default: durable `StoreModel` with recorder events; instance isolation by default, shared todos.
  3) Hybrid: parity by default; opt‑in durability per agent via config.
- Proposed Default: (2) Inspect default behind `parity_mode=false`; (1) when `parity_mode=true`.
- User Impact: durable state changes appear in logs; cross‑sample visibility possible; requires understanding of instance scoping.
- Test Impact: add store event assertions; adapt fixtures to initialize/clear stores.
- Migration Plan: provide helper `Files(instance=<name>)`; document shared vs isolated patterns; parity presets for examples.
- Status: Pending.

ID D2 — File Tools (ls/read/write/edit)
- Behavior (deepagents): cat‑n formatting; 2k per‑line truncation; offset/limit; uniqueness check for `edit_file` unless `replace_all=True`; error strings.
- Behavior (Inspect-native): same behavior on top of `StoreModel.Files` with standardized error codes/phrases.
- Options:
  1) String parity (match exact messages).
  2) Codes/phrases parity (stable codes + human text may vary slightly).
  3) Inspect envelope (tool output truncation wrapper + codes).
- Proposed Default: (2); keep messages close, assert on codes/phrases; enable Inspect truncation when configured.
- User Impact: clearer, structured errors; minor text differences.
- Test Impact: update tests to match codes/phrases; include truncation tests.
- Migration Plan: publish error code catalog; adapter for legacy tests (regex helpers).
- Status: Tentative.

ID D3 — Todos Tool Semantics
- Behavior (deepagents): `write_todos(todos)` replaces list; statuses `pending|in_progress|completed`; Command updates + ToolMessage.
- Behavior (Inspect-native): `Todos(StoreModel)` with get/set helpers; by default shared across agents; recorder emits store events.
- Options:
  1) Replace‑list only (parity).
  2) Add incremental ops (`add`, `update_status`, `remove`) as separate tools while keeping replace available.
  3) Keep single tool but accept op param (breaks strict parity).
- Proposed Default: (1) under `parity_mode=true`; (2) available when `parity_mode=false`.
- User Impact: optional richer operations; same states preserved.
- Test Impact: add CRUD coverage; parity path continues to pass.
- Migration Plan: deprecate raw replace in docs over time; keep for BC.
- Status: Pending.

ID D4 — Sub‑agent Orchestration & Message Shape
- Behavior (deepagents): `task(description, subagent_type)` runs another LangGraph agent; returns ToolMessage with final assistant content.
- Behavior (Inspect-native): `handoff()` to sub‑agent exposes `transfer_to_<name>` tool; boundary message “Successfully transferred to <agent_name>.”; assistant messages are prefixed with the agent name; system messages filtered.
- Options:
  1) Adapter to convert Inspect handoff transcript into deepagents‑like single ToolMessage (parity).
  2) Expose Inspect behavior directly and document boundary/prefixes (native).
  3) Configurable: adapter in `parity_mode=true`; native in `parity_mode=false`.
- Proposed Default: (3).
- User Impact: clearer boundaries in native mode; identical UX with parity.
- Test Impact: add assertions for boundary ChatMessageTool; keep adapter tests for parity.
- Migration Plan: document prefixing and message filtering; provide utility to strip boundaries for callers that need a single message.
- Status: Tentative.

ID D5 — Approvals/Interrupts Mapping (Respond Behavior)
- Behavior (deepagents): LangGraph interrupts with `allow_accept|allow_edit|allow_respond|allow_ignore(False)`; can emit tool response without execution (respond).
- Behavior (Inspect-native): `ApprovalPolicy` decisions `{approve, modify, reject, terminate}`; no built‑in “respond”.
- Options:
  1) Drop “respond” (recommend typed Reject + separate lightweight `respond()` tool later).
  2) Emulate respond by injecting a tool message (adapter) pre‑execution.
  3) Provide approver‑only `respond()` tool and recommend policy chains (auto→human).
- Proposed Default: (1) for core policy; (3) as optional follow‑up feature.
- User Impact: approval UX more explicit; no implicit respond.
- Test Impact: update approval tests to 4 decisions; add optional respond tool tests when implemented.
- Migration Plan: map `allow_respond` to explicit tool in configs; document differences.
- Status: Pending.

ID D6 — Model Resolver & Roles
- Behavior (deepagents): env‑driven LangChain model construction (Ollama/LM‑Studio) with per‑subagent overrides via model instance/dict.
- Behavior (Inspect-native): `resolve_model(provider, model, role)` returning either concrete model name or `inspect/<role>`; roles mapped via env.
- Options:
  1) Keep current env names (`DEEPAGENTS_*`) as compatibility layer; alias to Inspect vars.
  2) Introduce `INSPECT_*` vars; provide migration mapping.
  3) Role‑first config with fallback to explicit model.
- Proposed Default: (1)+(3): accept deepagents envs; prefer roles when provided.
- User Impact: minimal config churn; new role ergonomics.
- Test Impact: add precedence tests (role > model > provider env).
- Migration Plan: resolver docs with examples; deprecate only if needed.
- Status: Tentative.

ID D7 — Logging & Recorders
- Behavior (deepagents): none standardized; LangGraph messages only.
- Behavior (Inspect-native): transcript + span events + bundle to `.inspect/logs/` file recorder.
- Options:
  1) Off by default; enable with CLI flag.
  2) On by default in `dev`, off in `ci`.
  3) Always on; allow log dir override.
- Proposed Default: (2).
- User Impact: discoverable logs by default; opt‑out for CI noise.
- Test Impact: assert recorder files in smoke tests; avoid brittle paths.
- Migration Plan: README update; env knob `INSPECT_LOG_DIR`.
- Status: Pending.

ID D8 — Limits & Truncation Defaults
- Behavior (deepagents): not standardized.
- Behavior (Inspect-native): `message_limit`, `token_limit`, truncation strategies.
- Options: fixed defaults vs config; continue message on stall.
- Proposed Default: `message_limit=50`, truncation “auto”; continue message enabled.
- User Impact: safer defaults; predictable stop conditions.
- Test Impact: add overflow/truncation tests; track token usage.
- Migration Plan: document defaults; expose overrides in CLI.
- Status: Pending.

ID D9 — Tool Output Truncation Envelope
- Behavior (deepagents): raw tool output.
- Behavior (Inspect-native): standardized truncation wrapper enforced by generate config.
- Options: enable by default vs opt‑in.
- Proposed Default: enabled when `parity_mode=false`; disabled in parity.
- Impact: prevents jumbo outputs breaking context; tests must accept wrapper phrase.
- Status: Tentative.

ID D10 — Tool Argument Validation & Error Schema
- Behavior (deepagents): Python signature errors surface; no JSON Schema standardization.
- Behavior (Inspect-native): JSON Schema + YAML coercion; stable codes/phrases.
- Options: keep legacy exceptions vs standardize codes and document them.
- Proposed Default: standardized codes; map legacy failure types to codes.
- Impact: more reliable tests; slight error text differences.
- Status: Tentative.

ID D11 — Tool Parallelism Policy
- Behavior (deepagents): sequential.
- Behavior (Inspect-native): optional TaskGroup parallel tool calls with policy.
- Options: off by default; opt‑in via config; guard by approval rules.
- Proposed Default: off by default; document enablement + limits.
- Impact: potential speedup; concurrency hazards controlled via policy.
- Status: Pending.

ID D12 — Sandbox / Host FS Mode
- Behavior (deepagents): virtual in‑memory only.
- Behavior (Inspect-native): optional host FS via Inspect `text_editor`, gated by preflight and feature flag.
- Options: disabled by default; explicit opt‑in per run.
- Proposed Default: disabled; must pass readiness check and approval policy.
- Impact: enables real edits for power users; CI safe.
- Status: Pending.

ID D13 — Migration Shim (`create_deep_agent`)
- Behavior (deepagents API): `create_deep_agent(tools, instructions, model=None, subagents=None, builtin_tools=None, interrupt_config=None, checkpointer=None, ...)`.
- Behavior (Inspect-native): same signature building Inspect supervisor/sub‑agents/approvals under the hood.
- Options: strict signature parity vs minor additions.
- Proposed Default: strict parity; extras via keyword‑only params.
- Impact: drop‑in for most code; new features hidden unless requested.
- Status: Tentative.

ID D14 — Examples & CLI
- Behavior (deepagents): example scripts + LangGraph studio.
- Behavior (Inspect-native): `examples/inspect/*` + minimal dev CLI (`python -m inspect_agents.cli`).
- Options: parallel examples; document both paths.
- Proposed Default: keep both; mark Inspect as experimental until parity passes.
- Impact: smoother adoption.
- Status: Pending.

ID D15 — Retries & Cache
- Behavior (deepagents): none standardized.
- Behavior (Inspect-native): retry helpers + cache policy in generate calls.
- Options: disabled by default; enable via env/flags.
- Proposed Default: retries on transient errors enabled at low attempt count; cache opt‑in.
- Impact: robustness with bounded cost.
- Status: Pending.

ID D16 — Message Shapes & Prefixing (Sub‑agents)
- Behavior (deepagents): tool outputs often returned as `ToolMessage` content only; no agent prefixing.
- Behavior (Inspect-native): handoff boundary message; assistant messages prefixed with the agent name; system messages filtered.
- Options: adapter in parity; native otherwise.
- Proposed Default: adapter under `parity_mode=true`.
- Impact: downstream consumers parsing transcripts need update unless adapter used.
- Status: Tentative.

ID D17 — Env Var Compatibility
- Behavior (deepagents): `DEEPAGENTS_MODEL_PROVIDER`, `OLLAMA_*`, `LM_STUDIO_*`.
- Behavior (Inspect-native): introduce `INSPECT_*` while honoring deepagents envs.
- Options: maintain aliases indefinitely vs deprecate later.
- Proposed Default: maintain aliases; deprecate only with major version.
- Impact: zero‑cost migration for existing users.
- Status: Pending.

ID D18 — Approval Viewer Redaction
- Behavior (deepagents): N/A.
- Behavior (Inspect-native): redact sensitive args in approval viewer.
- Options: minimal vs opinionated redaction sets.
- Proposed Default: minimal built‑ins (keys, tokens, secrets), extensible via config.
- Impact: safer reviews; small effort to configure.
- Status: Pending.

ID D19 — Token Usage & Budgets Reporting
- Behavior (deepagents): not standardized.
- Behavior (Inspect-native): record token usage; enforce budgets; log at sample end.
- Options: disabled vs enabled by default.
- Proposed Default: enabled with warning at 80% and stop at 100% unless overridden.
- Impact: predictable costs; tests to assert budget notes in transcript.
- Status: Pending.

ID D20 — Submit Tool Semantics for Supervisor
- Behavior (deepagents): no explicit submit; loop termination via agent limits or caller.
- Behavior (Inspect-native): `react` includes an explicit submit path and optional scoring attempts.
- Options: disable submit in parity; enable when using scoring/attempts in native mode.
- Proposed Default: parity disables submit; native enables when scorer/task configured.
- Impact: affects termination tests and example flows.
- Status: Pending.

ID D21 — Checkpointer Parameter (API Parity)
- Behavior (deepagents): `checkpointer` parameter supported by LangGraph agent builders.
- Behavior (Inspect-native): no direct equivalent; transcripts and stores persist state.
- Options: accept and no‑op with warning; map to transcript persistence; drop in a major release.
- Proposed Default: accept + warn; document limitation in shim docs.
- Impact: preserves API compatibility short‑term.
- Status: Pending.

ID D22 — MCP / Remote Tools Exposure (Optional)
- Behavior (deepagents): not present.
- Behavior (Inspect-native): could expose MCP bridges; out of scope for parity.
- Options: keep off by default; document as extension.
- Proposed Default: off; feature‑flag later if needed.
- Impact: none for parity; future extensibility.
- Status: Pending.

Appendix A — Parity Controls
- `parity_mode` (bool): governs D1, D2, D4, D9, D16, D20 for strict deepagents‑like behavior.
- `inspect_log_dir`: path for recorder outputs (D7).
- `inspect_parallel_tools`: enable/disable parallelism (D11).
- `inspect_tool_output_max_bytes`: truncation limit (D9).

Appendix B — Test Categories to Add/Update
- Store events and persistence, including instance isolation.
- Tools behavior: formatting, truncation, uniqueness, structured errors.
- Handoff boundaries and message prefixing; adapter path.
- Approvals decisions and error surfaces; optional respond tool if implemented.
- Model resolver precedence; role mapping.
- Limits/truncation overflow and continue behavior.
- Retries/cache stubs; token budget logging.

Change Log
- 2025‑08‑31: Merged root draft into docs with expanded decision set and parity controls.

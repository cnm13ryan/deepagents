# Deviations vs DeepAgents — Decisions Pending

Purpose
- Track intentional or potential deviations from the original deepagents behavior while porting to Inspect‑AI. Each item lists the difference, options, impact, and links to the relevant TODOs. Use this to make informed choices (parity vs Inspect‑native).

1) Approval “respond” behavior
- Difference: deepagents supports a human “respond” that injects a tool-style reply; Inspect approvals only support approve/modify/reject/terminate.
- Options:
  - Emulate via hidden `respond()` tool used only by approver (parity).
  - Drop “respond” and use reject/terminate (Inspect‑native).
- Impact: UX parity in review loops; simpler policy if dropped.
- Related: `TODO-approval-mapping.md`, `TODO-approval-ux-chains.md`.

2) Sub‑agent reply shape and prefixes
- Difference: Inspect handoff inserts a boundary (“Successfully transferred …”), strips system messages, and prefixes assistant outputs with `[agent_name]`. deepagents’ task returns a single ToolMessage content without boundary/prefix.
- Options:
  - Parity mode: squash sub‑agent conversation into a single final reply; hide boundary & prefixes.
  - Inspect‑native: keep boundary + prefixes for provenance.
- Impact: Transcript readability vs drop‑in compatibility.
- Related: `TODO-subagent-orchestration.md`.

3) Parallel tool calls (concurrency)
- Difference: Inspect executes multiple tool_calls concurrently; deepagents does not specify parallelism.
- Options:
  - Parity default: serialize tool calls; opt‑in parallel per tool.
  - Inspect‑native: keep parallel by default.
- Impact: Ordering guarantees and side‑effect safety.
- Related: `TODO-parallel-tools.md`.

4) Tool error surface & validation messages
- Difference: Inspect emits JSON‑Schema validation aggregates and a standard truncation envelope; deepagents expects specific error intents (e.g., missing file, offset too large, uniqueness).
- Options:
  - Parity: normalize surface to stable codes/phrases matching deepagents’ expectations; keep Inspect details secondary.
  - Inspect‑native: adopt Inspect messages wholesale.
- Impact: Test brittleness vs richer diagnostics.
- Related: `TODO-tool-schema-and-errors.md`, `TODO-tool-output-truncation.md`, `TODO-virtual-fs-tools.md`.

5) System message handling in handoff
- Difference: Inspect removes system messages when delegating; deepagents sub‑agent may not.
- Options:
  - Parity: re‑inject essential system guidance for sub‑agents.
  - Inspect‑native: keep the removal.
- Impact: Prompt control vs stricter isolation.
- Related: `TODO-subagent-orchestration.md` (Filters).

6) Submit tool semantics for supervisor
- Difference: Inspect react defaults to a submit tool; deepagents’ LangGraph agent does not expose an explicit submit concept.
- Options:
  - Parity: use `react(..., submit=False)` and rely on loop termination by limits or external runner.
  - Inspect‑native: keep submit and (optionally) scoring attempts.
- Impact: Termination model and tests; simpler parity vs richer evaluation.
- Related: `TODO-supervisor-agent.md`, `TODO-scoring-and-tasks.md`.

7) Model selection environment semantics
- Difference: deepagents honors `DEEPAGENTS_MODEL_PROVIDER`, `OLLAMA_MODEL_NAME`, etc.; Inspect supports role/model strings.
- Options:
  - Parity: keep deepagents envs as aliases mapping to Inspect roles/models.
  - Inspect‑native: require Inspect‑specific env/flags.
- Impact: Migration friction vs clean Inspect config.
- Related: `TODO-model-resolver.md`, `TODO-model-roles.md`.

8) Checkpointer parameter
- Difference: deepagents `create_deep_agent` accepts `checkpointer`; Inspect provides transcripts and store but not a direct equivalent.
- Options:
  - Parity: accept and no‑op/log (or map to transcript persistence); document limitation.
  - Inspect‑native: remove from shim.
- Impact: API compatibility vs clarity.
- Related: `TODO-migration-shim.md`.

9) Token budgets and costs
- Difference: deepagents doesn’t enforce budgets; Inspect exposes token usage and limits.
- Options:
  - Advisory: warn on budget exceed.
  - Enforced: terminate on exceed.
- Impact: Safety vs flexibility in long sessions.
- Related: `TODO-limits-and-truncation.md`.

10) Logs/recorders/transcripts default
- Difference: deepagents had no standardized recorder; Inspect does.
- Options:
  - Optional by default; enable via flag in examples.
  - Always on.
- Impact: Disk usage/noise vs observability.
- Related: `TODO-logging-recorders.md`.

11) Host FS vs virtual FS default
- Difference: deepagents defaults to virtual (mock) FS; Inspect can edit host FS via sandbox.
- Options:
  - Parity: default Store‑backed FS; host FS opt‑in.
  - Inspect‑native: host FS default in sandboxed envs.
- Impact: Safety & determinism vs real‑world utility.
- Related: `TODO-sandbox-host-fs-mode.md`, `TODO-sandbox-health.md`.

12) MCP/remote tools exposure (optional)
- Difference: Not present in deepagents.
- Options: keep off by default; document as extension only.
- Related: future MCP docs.

Decision Tracking
- Until decisions are finalized, implement a `parity_mode` flag that toggles items 2–4 & 6 (reply shaping, serialization, error surface, submit usage). Document defaults in `TODO.md` once settled.


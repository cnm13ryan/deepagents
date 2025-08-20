# Inspect Core Learnings → DeepAgents Integration

Purpose: Encode Inspect’s high‑leverage patterns into DeepAgents to enable fast prototyping, measurable iteration, and a path to reliable, autonomous agentic systems.

## Guiding Goal

Fast prototyping of simple and powerful agentic systems, with smooth integration of tools/techniques to learn and iterate quickly, accelerating toward reliable autonomy.

## Core Learnings To Internalize

1) Evaluation‑First Development
- Treat evals as the development loop. Every change should be easy to measure.
- Provide a tiny eval kit that runs curated suites against any DeepAgents graph.

2) Separation of Concerns: Tasks, Solvers, Scorers
- Tasks describe the problem; Solvers/Agents execute; Scorers judge.
- Keep these orthogonal to swap strategies and compare fairly.

3) Reproducibility, Logging, and Tracing
- Make runs replayable and comparable: capture model config, env, git ref, transcripts, tool calls, state deltas, artifacts, and scores.
- Bundle runs for sharing and RCA.

4) Reliability Budgets and Controls
- Explicit caps (time, tokens, messages, recursion), retries with backoff, and fail‑fast thresholds.
- Deterministic seeds for sampling; per‑sample timeouts.

5) Sandbox and Isolation
- Default to the mock FS; offer optional real sandboxes for file/process tools.
- Parallelism limits and cleanup semantics matter for stability.

6) Human‑in‑the‑Loop Approvals
- Controlled autonomy with clear escalation (auto/deny/escalate).
- Console and UI approvals; pluggable policy config.

7) Model Roles and Provider Agnosticism
- Swap models/roles without code changes; log generation config centrally.
- Support per‑subagent overrides and role‑based routing.

8) Suites that Measure Learning Velocity
- Target what the loop must do well: plan adherence, tool correctness, delegation, research/citation quality, and regression guards.

9) CI Quality Gates and Baselines
- Fast smoke suites for PRs; nightly/full suites for depth.
- Baseline comparisons with tolerances to block regressions.

10) Developer Ergonomics
- One‑liners to try ideas and see impact; filters for speed; clear reports.

## Concrete Adoption In DeepAgents

- Evals Kit and CLI
  - Add `deepagents.evals` (Python) and `deepagents eval` (CLI) wrapping Inspect’s runner.
  - Support suites, baselines, bundle/export, and HTML/Markdown summaries.

- Solver Adapter
  - Adapter to run any DeepAgents graph as an Inspect solver (Task→invoke→collect outputs/metrics).

- Scorers
  - Deterministic: exact match, regex, JSON‑schema, MCQ.
  - Optional LLM‑judge wrappers for qualitative checks.

- Telemetry Hooks
  - Emit standardized events for `write_todos`, `read_file`, `edit_file`, and `task` to compute:
    - Plan hygiene (pending/in_progress/completed discipline)
    - Edit success/ambiguity/rollback rate
    - Delegation count and success ratio
    - Token/time/tool error metrics

- Reliability Config in `create_deep_agent`
  - Budgets (time/token/message/recursion), retries/backoff, parallel subagent caps.
  - Log all limits into run metadata for comparisons.

- Sandbox Backends
  - Keep mock FS default; add opt‑in temp‑dir / container sandboxes for real tools.

- Approvals
  - Policy‑driven approval for tool calls (auto/deny/escalate); console flows in CLI and Studio.

## Starter Suites

- Plan‑Adherence: checks TODO usage discipline and progress updates.
- File‑Edit‑Correctness: enforces read‑before‑edit, uniqueness or `replace_all`, and exact replacements.
- Subagent‑Delegation: verifies decomposition and “context quarantine” usage via `task`.
- Research‑Citations: validates citation presence/format and basic completeness for reports.
- Regression: pinned cases for known failure modes.

## Developer UX

- CLI examples:
  - `deepagents eval plan-adherence --agent examples/research/run_local.py:build_agent --log-dir runs/$(date +%F) --trace`
  - `deepagents report --log-dir runs/2025-08-20 --compare runs/baseline`
  - `deepagents bundle --log-dir runs/2025-08-20 --out bundles/run-2025-08-20`

## Near‑Term Backlog (MVP)

1) `deepagents.evals` wrapper + `deepagents eval` CLI
2) Telemetry hooks in built‑in tools and `task`
3) Reliability options on `create_deep_agent` + logging
4) Implement “plan‑adherence” micro‑suite
5) CI smoke‑eval job with artifact uploads and baseline diff

## Signals and Metrics

- Pass/fail per suite; trend lines across runs.
- Plan metrics (in_progress uniqueness, completion latency).
- Tool metrics (edit success, ambiguous‑edit errors, read‑before‑edit violations).
- Delegation metrics (spawn count, success ratio, loop depth).
- Cost/latency (tokens/time per run and per sample).


# Project Status — DeepAgents

Updated: 2025-09-03

Legend
- DONE: feature shipped and exercised by examples/tests
- PARTIAL: some sub‑items done; notable gaps remain
- TODO: not started or design only

Source of truth
- Rewrite backlog: docs/backlog/rewrite/README.md
- Todos backlog: docs/backlog/todos/README.md and related files
- Tests: tests/unit/inspect_agents and tests/integration/inspect_agents

High‑Level Summary
- Core Inspect‑AI rewrite: MOSTLY DONE
- Sandbox/filesystem safety (ADR‑0004): PARTIAL
- Approvals & chains: DONE
- Parallel tools & handoff exclusivity: PARTIAL
- Limits & truncation (tool output): TODO
- Retry/cache surfaces: TODO
- CI/submodules bootstrap: TODO

Themes

1) Inspect‑AI Rewrite Core
- DONE: Supervisor Agent (ReAct) — docs/backlog/rewrite/TODO-supervisor-agent.md
- DONE: Sub‑agent Orchestration (handoff/as_tool) — docs/backlog/rewrite/TODO-subagent-orchestration.md
- DONE: Migration Shim (create_deep_agent parity) — docs/backlog/rewrite/TODO-migration-shim.md
- DONE: Config Loader (YAML) — docs/backlog/rewrite/TODO-config-loader.md
- DONE: Model Resolver — docs/backlog/rewrite/TODO-model-resolver.md; ADR: docs/adr/0002-model-roles-map.md
- TODO: Model Roles Map (role wiring/strict mode/docs) — docs/backlog/rewrite/TODO-model-roles.md and docs/backlog/TODO-model-roles-map.md

2) Tools (Todos, Virtual FS, Schema)
- DONE: Canonical tools rework (Todos + unified FS tools) — docs/backlog/rewrite/TODO-canonical-tools-rework.md
- DONE: Virtual FS tools (ls/read/write/edit/delete) — docs/backlog/rewrite/TODO-virtual-fs-tools.md
- DONE: Tool argument schema & errors — docs/backlog/rewrite/TODO-tool-schema-and-errors.md
- TODO: Tool timeouts & cancellation — docs/backlog/rewrite/TODO-tool-timeouts-cancellation.md
- TODO: Tool output truncation defaults & env override — docs/backlog/rewrite/TODO-tool-output-truncation.md, TODO-max-tool-output-default.md, TODO-env-max-tool-output-override.md

3) Sandbox & Filesystem Safety (ADR‑0004)
- PARTIAL: Root confinement, symlink denial, byte ceilings, observability hygiene, and sandbox ls rooting implemented — see docs/backlog/todos/0004-sandbox-fs-todo.md
- TODO: Read‑only mode flag; safer edit (expected_count/dry_run); docs surfacing; TTL recheck; preflight gating/logging/mode toggle/reset cache/tests — docs/backlog/todos/0004-sandbox-fs-todo.md and docs/backlog/rewrite/*sandbox-preflight*.md

4) Approvals & Human‑in‑the‑Loop
- DONE: Approval mapping + presets (ci/dev/prod) and UX chains — docs/backlog/rewrite/TODO-approval-mapping.md, TODO-approval-ux-chains.md
- DONE: Handoff exclusivity policy at approver layer — src/inspect_agents/approval.py::handoff_exclusive_policy()
- TODO: Executor‑level gating + transcript “skipped” events — docs/backlog/todos/feature-handoff-exclusivity.md, feature-skipped-tool-events.md

5) Parallel Tools Policy
- PARTIAL: Two parallel‑safe tools execute; handoff tools declare serial — tests/integration/inspect_agents/test_parallel.py
- TODO: Ensure “handoff + other tool” executes only the handoff (currently xfail) — same test file

6) Limits & Truncation (Global)
- TODO: Limits & truncation docs/impl — docs/backlog/rewrite/TODO-limits-and-truncation.md
- TODO: Default max_tool_output + env override; tests for default/precedence — TODO-max-tool-output-default.md; TODO-env-max-tool-output-override.md; TODO-truncation-default-limit-test.md; TODO-truncation-envelope-counts.md; TODO-truncation-log-effective-limit.md

7) Retry & Cache
- TODO: Cache policy surface; retry policy via GenerateConfig; tests — docs/backlog/todo_feature_cache_policy.md; todo_feature_retry_policy.md; todo_feature_retry_cache_tests.md

8) CI & Developer Experience
- DONE: Run utility (examples/inspect/run.py); prompt task wiring (examples/inspect/prompt_task.py)
- TODO: CI & submodule bootstrap (checkout submodules, pin & update cadence) — docs/backlog/rewrite/TODO-ci-submodule-bootstrap.md
- TODO: Logging recorders — docs/backlog/rewrite/TODO-logging-recorders.md

9) Examples Parity
- DONE: Example 1 (inspect run utility + README) — examples/inspect/run.py
- DONE: Example 2 (sub‑agent + approvals demo) — examples/inspect/subagent_approvals_demo.py

How to Update This File
- Treat STATUS.md as a convenience index; authoritative details live in the docs/backlog items and tests.
- When a theme’s last blocking item lands (code + tests/docs), flip its status here in the same PR.


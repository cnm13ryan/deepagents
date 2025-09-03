# DeepAgents Documentation Index

This is the entry point for the DeepAgents documentation. It organizes all existing Markdown files into clear categories.

## Getting Started
- Inspect Agents Quickstart: `./getting-started/inspect_agents_quickstart.md`
- Inspect Console Cheat Sheet: `./getting-started/inspect_console_cheatsheet.md`

## Guides (How‑To)
- Stateless vs Stateful Tools — Harmonized (canonical): `./guides/stateless-vs-stateful-tools-harmonized.md`
- Canonical and Standard Tools — Umbrellas: `./guides/tool-umbrellas.md`
- Sub‑agent Recipes: `./guides/subagents.md`
- Supervisor Limits & Observability — Practical Guide: `./guides/supervisor-limits.md`
- Retries & Cache — Design, Config, and Defaults: `./guides/retries_cache.md`
- Approvals & Policies — How‑To: `./how-to/approvals.md`
- Filesystem Tools — Store vs Sandbox: `./how-to/filesystem.md`
- Operations: Logging & Tracing: `./how-to/operations_logging_tracing.md`

## Reference
- Environment Variables: `./reference/environment.md`
- Tools Reference Index: `./tools/README.md`

## Design Notes
- DeepAgents Implementation Prompts: `./design/deepagents_implementation_prompts.md`

## Architectural Decisions (ADRs)
- D0002 — Model Roles Map — Env‑Driven Resolution: `./adr/0002-model-roles-map.md`
- D0003 — Supervisor Limits & Observability: `./adr/0003-supervisor-limits-and-observability.md`
- D0004 — Filesystem Sandbox Mode — Guardrails and Defaults: `./adr/0004-filesystem-sandbox-guardrails.md`
- D0004 — Tool Output Truncation Defaults: `./adr/0004-tool-output-truncation.md`
- D0005 — Tool Parallelism and Handoff Exclusivity: `./adr/0005-tool-parallelism-policy.md`

See `./adr/README.md` for a compact ADR index.

## Backlog

Root Backlog (status):
- PARTIAL — Model Roles Map — Implementation Checklists: `./backlog/TODO-model-roles-map.md`
- TODO — Configurable Cache Policy: `./backlog/todo_feature_cache_policy.md`
- TODO — Retry Policy Surface: `./backlog/todo_feature_retry_policy.md`
- TODO — Retry/Cache Tests: `./backlog/todo_feature_retry_cache_tests.md`

Todos folder (limits, sandbox, features): see `./backlog/todos/README.md`.

Inspect‑AI Rewrite backlog: see `./backlog/rewrite/README.md` (index updated with DONE/TODO).

## Deprecated/Archived
- Stateless vs Stateful Tools (Inspect Tool Support) — superseded by the Harmonized guide: `./guides/archive/stateless-vs-stateful-tools.md`
- What is the difference between stateless and stateful tools? — superseded by the Harmonized guide: `./guides/archive/stateless-vs-stateful-tools-1.md`

## Contributing to Docs
- Prefer linking to canonical pages (e.g., Harmonized stateless/stateful guide).
- Use relative links under `docs/`.
- Propose file moves/renames via PR; avoid breaking URLs without stubs.

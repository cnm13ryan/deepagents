# docs: Inspect-AI Rewrite — Feature TODOs

This folder contains self-contained, actionable TODO checklists for each feature in the Inspect-AI–native rewrite of deepagents. Work on the `inspect-ai-rewrite` branch. Complete and commit each feature atomically.

Features
- [ ] Core State Models — see `TODO-core-state-models.md`
- [ ] Todos Tooling — see `TODO-todos-tooling.md`
- [ ] Virtual FS Tools — see `TODO-virtual-fs-tools.md`
- [ ] Model Resolver — see `TODO-model-resolver.md`
- [ ] Supervisor Agent — see `TODO-supervisor-agent.md`
- [ ] Sub-agent Orchestration — see `TODO-subagent-orchestration.md`
- [ ] Run Utility — see `TODO-run-utility.md`
- [ ] Tool Approval Mapping — see `TODO-approval-mapping.md`
- [ ] Sandbox/Host FS Mode (optional) — see `TODO-sandbox-host-fs-mode.md`
- [ ] Migration Shim — see `TODO-migration-shim.md`
- [ ] Examples Parity — see `TODO-examples-parity.md`
- [ ] CI & Submodule Bootstrap — see `TODO-ci-submodule-bootstrap.md`

Additional Cross-Cutting TODOs
- [ ] Scoring & Tasks — see `TODO-scoring-and-tasks.md`
- [ ] Tool Timeouts & Cancellation — see `TODO-tool-timeouts-cancellation.md`
- [ ] Logging & Recorders — see `TODO-logging-recorders.md`
- [ ] Limits & Truncation — see `TODO-limits-and-truncation.md`
- [ ] Retries & Cache — see `TODO-retries-and-cache.md`
- [ ] Tool Parallelism Policy — see `TODO-parallel-tools.md`
- [ ] Tool Argument Schema & Errors — see `TODO-tool-schema-and-errors.md`
- [ ] Tool Output Truncation — see `TODO-tool-output-truncation.md`
- [ ] Approval UX & Chains — see `TODO-approval-ux-chains.md`
- [ ] Sandbox Readiness Check — see `TODO-sandbox-health.md`
- [ ] Config Loader (YAML) — see `TODO-config-loader.md`
- [ ] Model Roles Map — see `TODO-model-roles.md`
- [ ] Dev CLI — see `TODO-dev-cli.md`

Decisions & Defaults (Recommendations)
- State Isolation: Files isolated by default per agent via `StoreModel.instance`; Todos shared by default. Allow explicit sharing when needed.
- File Tools Mode: Default to Store-backed virtual FS. Host FS via `text_editor` is opt-in behind a feature flag and sandbox check.
- Delegation Mechanism: Default to `handoff()` for sub-agents; expose `as_tool()` for single-shot utilities.
- Error/Message Parity: Target near-parity with stable error codes/phrases; avoid brittle full-string matching in tests.
- Model Defaults: Prefer local (Ollama) when available; otherwise require explicit env configuration and fail fast with clear guidance.
- Approval Policies: Use per-tool granular policies with environment presets (ci/dev/prod). CI: auto-approve except network/FS; prod: escalate sensitive tools.
- Approver “Respond”: Do not simulate within approval decisions; consider a future, approver-only `respond()` tool as a separate feature if needed.
- Submodule Pinning: Pin Inspect-AI to a tagged release/commit; update on a monthly cadence or as-needed via PR.
- Branch Strategy: Push `inspect-ai-rewrite` early as a draft PR to enable CI and shared visibility; track progress via these TODOs.

# docs(supervisor): Adopt hybrid limits + observability defaults
---
Title: D0003 — Supervisor Limits & Observability
Status: Accepted
Date: 2025-09-03
---

Context
- The supervisor is implemented via Inspect’s `react(..., submit=True)` with `attempts` plumbed. Sub‑agents are wrapped using `handoff(..., limits=...)`. Top‑level runs may pass `limits` via the runner (`agent_run(..., limits=...)`).  
  Pointers: `build_supervisor()` returns `react()` without `limits`; sub‑agents pass `limits` to `handoff()`. Runner forwards `limits`.  
- We need deterministic guardrails and clear observability, without fighting Inspect’s built‑in limit semantics.

Decision
- Enforcement Scope: Use a hybrid strategy.  
  - Runner/sample level: apply global budgets (wall‑clock, tokens if used) via the runner’s `limits` parameter.  
  - Agent/sub‑agent level: apply targeted `limits` only at handoffs (`handoff(..., limits=[...])`). Do not add an explicit `limits` parameter to `build_supervisor()`.
- Defaults:  
  - `attempts=1` for the supervisor (minimal, submit‑terminated loop).  
  - No default token limit at supervisor level; if required, set at runner level with generous headroom.  
  - Prefer deterministic limits for tests: message or tool‑call limits in handoffs; wall‑clock at runner level with slack.  
- Observability: emit structured “limit_nearing” (≥80%) and “limit_exceeded” events; include `agent_name`, `scope`, `limit_kind`, `threshold`, `used`, and `exceeded_by` where applicable. User‑visible footers are off by default.

Rationale
- Aligns with existing architecture:  
  - Supervisor: `react(..., submit=True)` without local `limits` keeps the top‑level loop simple and model‑agnostic.  
  - Sub‑agents: per‑handoff `limits` provide localized circuit‑breakers where risk/cost concentrates.  
  - Runner: a single choke‑point for global budgets and reporting.  
- Determinism: message/tool‑call limits are stable in tests; token/time limits vary by model/system.

Implementation Notes
- Keep `build_supervisor(prompt, tools, attempts, model, truncation)` as is.  
- Continue passing `limits` into `handoff(...)` for sub‑agents and into the runner (`run_agent(..., limits=...)`).  
- Add structured logs when limits cross 80% and when exceeded; prefer JSON single‑line records keyed by `limit_*` fields.  
- Provide a small helper for composing common limits (e.g., `message_limit(n)`, `tool_call_limit(n)`) in examples/tests.

Testing
- Add integration tests that:  
  1) Hit an agent‑level message limit in a handoff and assert early exit + surfaced reason.  
  2) Hit a runner wall‑clock limit with a noop agent and assert early exit.  
  3) Ensure supervisor with `attempts>1` performs multiple ReAct turns before submit (smoke).

Consequences
- Clear separation of concerns: tuning global budgets does not require touching supervisor code.  
- Sub‑agents remain self‑contained with explicit guardrails.

Rollout
- Document usage in a user‑facing guide (`docs/supervisor-limits.md`).  
- Optional CLI flags: `--limit message=24`, `--limit time=90s` mapped to runner/sub‑agent as appropriate.


# feat(docs): add Retries & Cache guidance for agents

# Retries & Cache — Design, Config, and Defaults

This document records the design choices and recommended defaults for adding retries and model-response caching to Inspect‑AI–based agents in this repo.

Why
- Improve robustness against transient provider issues (rate limits, 5xx, timeouts).
- Reduce latency and cost by reusing identical generations where safe.

Inspect‑AI Capabilities (source of truth)
- Model.generate supports `cache: bool | CachePolicy` and writes/reads entries when enabled. 〖F:external/inspect_ai/src/inspect_ai/model/_model.py†L600-L627〗
- CachePolicy allows expiry/per‑epoch/scopes. 〖F:external/inspect_ai/src/inspect_ai/model/_cache.py†L58-L96〗
- Retries/backoff are handled inside Model._generate via `tenacity` using `GenerateConfig.max_retries` and `timeout`: exponential backoff with jitter, bounded by attempts and/or timeout. 〖F:external/inspect_ai/src/inspect_ai/model/_model.py†L587-L596〗 〖F:external/inspect_ai/src/inspect_ai/model/_retry.py†L31-L48〗
- The simple ReAct `basic_agent` already forwards a `cache` argument into `get_model().generate(...)`. 〖F:external/inspect_ai/src/inspect_ai/solver/_basic_agent.py†L186-L189〗
- The extensible `react` agent calls a generated Agent function that invokes `get_model(...).generate(...)` without exposing a `cache` parameter directly; passing a custom model Agent lets us inject cache/config cleanly. 〖F:external/inspect_ai/src/inspect_ai/agent/_react.py†L459-L465〗

Design Principles (repo‑specific)
- Keep imports light at module top; do heavy/optional imports locally inside functions. 〖F:src/inspect_agents/agents.py†L79-L93〗
- Prefer env‑first configuration with safe defaults; support per‑agent overrides using `__<AGENT_NAME>` suffix normalization (see quarantine filters). 〖F:src/inspect_agents/filters.py†L162-L170〗 〖F:src/inspect_agents/filters.py†L186-L205〗
- Mirror some flags via CLI that write env vars before constructing agents (examples runner). 〖F:examples/inspect/run.py†L85-L118〗 〖F:examples/inspect/run.py†L142-L161〗

Configuration Surface (proposed)
- Env vars (global defaults; can be overridden per sub‑agent via `__<AGENT_NAME>` suffix):
  - `INSPECT_AGENTS_CACHE` = `0|1` (default: 0)
  - `INSPECT_AGENTS_CACHE_EXPIRY` = e.g., `1D`, `1W` (default when cache on: `1W`)
  - `INSPECT_AGENTS_CACHE_PER_EPOCH` = `0|1` (default: 1)
  - `INSPECT_AGENTS_MAX_RETRIES` = int or `0` (default: 0 in CI/tests; 2 elsewhere)
  - `INSPECT_AGENTS_TIMEOUT_S` = int seconds (default: 60)
  - Per‑agent overrides: append `__<normalized_agent_name>` (e.g., `INSPECT_AGENTS_CACHE__research_writer=1`). 〖F:src/inspect_agents/filters.py†L162-L170〗

- API extensions:
  - `build_supervisor(..., cache: bool|CachePolicy|None = None, max_retries: int|None = None, timeout_s: int|None = None)`
  - `build_subagents(configs: list[SubAgentCfg], ...)` accepts optional keys per sub‑agent: `cache`, `cache_expiry`, `cache_per_epoch`, `max_retries`, `timeout_s`.
  - Precedence: explicit args > SubAgentCfg fields > env (global or per‑agent) > hard defaults.

Recommended Defaults by Mode
- CI/tests:
  - cache=off; max_retries=0; timeout_s=60.
  - Only enable cache in dedicated tests that assert caching behavior.
- Interactive (local dev):
  - cache=off by default; if enabled, expiry=1D, per_epoch=false; max_retries=2; timeout_s=60.
- Batch/Evals:
  - cache=on; expiry=1W; per_epoch=true; max_retries=2–3; timeout_s=90.

When NOT to Cache (or Scope Caching)
- Time‑sensitive prompts (“today”, “latest”), or agents using `web_search`/`web_browser_*`: keep cache off or use a short expiry (1–6h) and a time‑bucket scope (e.g., `scopes={"time_bucket": YYYYMMDD}`) to force periodic refresh.
- Sensitive content: if prompts/completions may include secrets/URLs/PII, prefer cache off; if needed, use short expiry and a per‑run scope key.
- Highly stochastic generations (high temperature or varying toolsets): cache offers limited benefit and may surprise with atypical replays.

Retry Policy Guidance
- Source of truth is Inspect’s internal retry (`GenerateConfig.max_retries`, `timeout`), which already implements exponential backoff with jitter; avoid adding another tenacity layer. 〖F:external/inspect_ai/src/inspect_ai/model/_retry.py†L31-L48〗
- Suggested caps: CI=0; Interactive=2; Batch=2–3. Timeouts: 60–120s depending on mode.
- Always set a finite cap (attempts and/or timeout) to prevent pathological waiting.

Implementation Sketch (non‑breaking)
1) Add a tiny “model bridge agent” to carry cache + generate config into `react` by acting as the `model` parameter:
   - The bridge signature: `async def agent(state, tools)` then `state.output = await get_model(resolved_model).generate(state.messages, tools, config=GenerateConfig(max_retries=..., timeout=...), cache=cache)`; append `state.output.message` and return state. 〖F:external/inspect_ai/src/inspect_ai/agent/_react.py†L459-L465〗
   - Keeps imports local and avoids changes to external Inspect‑AI.
2) Extend `build_supervisor` and `build_subagents` to accept the new knobs; compute values from per‑agent config/env (normalize agent names like quarantine filters). 〖F:src/inspect_agents/agents.py†L196-L207〗 〖F:src/inspect_agents/filters.py†L162-L170〗
3) Tests: add focused tests that (a) simulate a transient failure to assert a retry, (b) assert cache reuse on identical inputs by verifying cache read/write events in the transcript, and (c) ensure cache remains off for tests that depend on token accounting or message flow.

Observability
- Inspect’s transcript already records cache=`read|write` in `ModelEvent`; surface simple counters (hits/misses) in logs for visibility. 〖F:external/inspect_ai/src/inspect_ai/model/_model.py†L641-L647〗

FAQ
- Why not enable cache globally by default? Tests and time‑sensitive interactions can break or hide regressions; opt‑in avoids surprises.
- Why use a wrapper/bridge instead of patching Inspect? This repo deliberately wraps Inspect and keeps top‑level imports light; a wrapper keeps changes local, reversible, and consistent with existing design.


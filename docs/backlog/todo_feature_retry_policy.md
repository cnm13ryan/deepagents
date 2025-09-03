# TODO — Feature 2: Retry Policy Surface via GenerateConfig

Context & Motivation
- Purpose: Expose transient failure handling (max attempts, backoff, jitter) through our agent builders using Inspect’s native retry config.
- Problem: No way to set retries/timeouts from `build_supervisor`/`build_subagents`; transient HTTP/timeouts fail user runs even when a retry would succeed.
- Impact: Improved resiliency under rate limits and flaky providers with bounded tail latency.
- Constraints: Do not add a second retry layer; rely on `GenerateConfig(max_retries, timeout)` which drives tenacity’s exponential jitter. No edits to `external/inspect_ai`.

Implementation Guidance
- Primary files to examine
  - `src/inspect_agents/agents.py` — extend function signatures and plumb into model bridge. 〖F:src/inspect_agents/agents.py†L96-L138〗 〖F:src/inspect_agents/agents.py†L153-L207〗
  - `external/inspect_ai/src/inspect_ai/model/_generate_config.py` — fields `max_retries`, `timeout`. 〖F:external/inspect_ai/src/inspect_ai/model/_generate_config.py†L120-L150〗
  - `external/inspect_ai/src/inspect_ai/model/_retry.py` — policy: wait_exponential_jitter + stop conditions. 〖F:external/inspect_ai/src/inspect_ai/model/_retry.py†L31-L48〗
  - `external/inspect_ai/src/inspect_ai/model/_model.py` — tenacity decorator around provider generate. 〖F:external/inspect_ai/src/inspect_ai/model/_model.py†L587-L596〗
- Greppable identifiers
  - `GenerateConfig(`, `max_retries`, `timeout`, `model_retry_config`, `wait_exponential_jitter`.
- Pattern snippet
  - Pass `GenerateConfig(max_retries=..., timeout=...)` to `get_model().generate(...)` via the model bridge; do not wrap with any extra retry logic.

Scope Definition
- Implement
  - Extend `build_supervisor(..., max_retries: int|None = None, timeout_s: int|None = None)`.
  - Extend `SubAgentCfg` with optional `max_retries: int|None`, `timeout_s: int|None`.
  - Update the model bridge to merge an on‑the‑fly `GenerateConfig` containing these values.
  - Env parsing (global + per‑agent overrides): `INSPECT_AGENTS_MAX_RETRIES`, `INSPECT_AGENTS_TIMEOUT_S` (and `...__<AGENT_NAME>` variants).
- Modify
  - `src/inspect_agents/agents.py` and the bridge helper module if separate.
- Avoid
  - Any custom retry wrappers beyond Inspect’s.

Success Criteria
- Behavior
  - With `max_retries>0`, a transient error classified as retryable is retried and the call succeeds on a subsequent attempt.
- Configuration
  - Precedence: explicit args > per‑agent env > global env > defaults. Sensible defaults: CI=0, interactive=2, batch=2–3; timeout 60–120.
- Tests
  - Dedicated retry test (see tests TODO) simulates one transient failure then success using `mockllm` + monkeypatched `Model.should_retry`.

Task Checklist
- [ ] Add `max_retries`, `timeout_s` args to `build_supervisor` and plumb through.
- [ ] Extend `SubAgentCfg` with `max_retries`, `timeout_s` (NotRequired).
- [ ] Update model bridge to merge `GenerateConfig(max_retries=..., timeout=...)`.
- [ ] Parse env defaults and per‑agent overrides using suffix normalization.
- [ ] Add targeted retry test and ensure offline determinism.
- [ ] Update `docs/retries_cache.md` if syntax or defaults change.

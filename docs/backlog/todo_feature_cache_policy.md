# TODO — Feature 1: Configurable Cache Policy for Supervisor/Sub‑agents

Context & Motivation
- Purpose: Enable opt‑in model response caching for supervisor and sub‑agents to cut latency and cost on repeated generations while keeping correctness intact.
- Problem: `build_supervisor`/`build_subagents` do not expose Inspect’s cache; users cannot enable reuse without editing callsites.
- Impact: Faster repeated runs (interactive or eval epochs), lower provider spend; defaults remain safe for tests/time‑sensitive flows.
- Constraints: No edits to `external/inspect_ai`; keep top‑level imports light; follow env‑first configuration with per‑agent overrides.

Implementation Guidance
- Primary files to examine
  - `src/inspect_agents/agents.py` — `build_supervisor`, `build_subagents`. 〖F:src/inspect_agents/agents.py†L96-L138〗 〖F:src/inspect_agents/agents.py†L153-L207〗
  - `src/inspect_agents/filters.py` — per‑agent env suffix and env precedence patterns. 〖F:src/inspect_agents/filters.py†L162-L170〗 〖F:src/inspect_agents/filters.py†L186-L205〗
  - `external/inspect_ai/src/inspect_ai/agent/_react.py` — accepts `model: str|Model|Agent`; using an Agent bridge lets us inject cache cleanly. 〖F:external/inspect_ai/src/inspect_ai/agent/_react.py†L459-L465〗
  - `external/inspect_ai/src/inspect_ai/model/_model.py` — `Model.generate(..., cache=...)` and cache read/write. 〖F:external/inspect_ai/src/inspect_ai/model/_model.py†L600-L627〗
  - `external/inspect_ai/src/inspect_ai/model/_cache.py` — `CachePolicy(expiry, per_epoch, scopes)`. 〖F:external/inspect_ai/src/inspect_ai/model/_cache.py†L58-L96〗
- Greppable identifiers
  - `def build_supervisor(`, `def build_subagents(`, `CachePolicy`, `get_model().generate`, `_model_generate`.
- Pattern snippet to emulate (local imports):
  - Agents keep heavy deps inside functions (see `_built_in_tools()` local imports). 〖F:src/inspect_agents/agents.py†L79-L93〗

Scope Definition
- Implement
  - Extend `build_supervisor(..., cache: bool|CachePolicy|None = None)`.
  - Extend `SubAgentCfg` with optional `cache: bool|CachePolicy` and sugar fields `cache_expiry: str|None`, `cache_per_epoch: bool|None`.
  - Create a tiny model‑bridge Agent (helper) that calls `get_model(resolved).generate(state.messages, tools, cache=cache, config=...)` and appends `state.output.message` before return.
  - Env parsing with per‑agent overrides (suffix normalization from filters):
    - `INSPECT_AGENTS_CACHE`, `INSPECT_AGENTS_CACHE_EXPIRY`, `INSPECT_AGENTS_CACHE_PER_EPOCH` and `...__<AGENT_NAME>` variants.
- Modify
  - `src/inspect_agents/agents.py` (signatures + wiring to bridge).
  - Optionally add `src/inspect_agents/model_bridge.py` if not inlined.
- Avoid
  - Changing `external/inspect_ai`.
  - Enabling cache by default for existing tests.

Success Criteria
- Functionality
  - When `cache=True` or a `CachePolicy(...)` is provided (arg or env), identical inputs produce a cache read on the second call (provider not re‑invoked).
- Configuration
  - Precedence: explicit args > per‑agent env > global env > defaults.
- Tests
  - A dedicated test demonstrates cache write on first run and cache read on second (see Feature 3 test TODO).
- Compatibility
  - Omitting `cache` leaves behavior unchanged.

Task Checklist
- [ ] Add optional `cache` param to `build_supervisor` and plumb through.
- [ ] Extend `SubAgentCfg` TypedDict with `cache`, `cache_expiry`, `cache_per_epoch`.
- [ ] Implement a model bridge Agent to inject `cache` into `get_model().generate`.
- [ ] Read env defaults + per‑agent overrides using the filters’ suffix normalization.
- [ ] Document envs in `docs/retries_cache.md` and update examples if needed.
- [ ] Add targeted cache test (see tests TODO file).

---

# Notes
- Keep imports local to functions to preserve startup cost characteristics.
- Consider adding an optional `scopes` time bucket (e.g., YYYYMMDD) later; out of scope for the first pass.

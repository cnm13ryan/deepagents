# TODO — Feature 3: Tests for Transient Retry and Cached Reuse

Context & Motivation
- Purpose: Provide focused, offline tests proving (a) transient failure retry works via `GenerateConfig.max_retries`, and (b) cache reuse avoids duplicate provider calls.
- Problem: Without tests, enabling cache/retries risks regressions and unclear behavior; existing suites don’t cover these cases.
- Impact: Confidence to ship; catch misconfigurations early; keep cache default off elsewhere.
- Constraints: Offline only (`NO_NETWORK=1`); deterministic; avoid modifying unrelated failing suites.

Implementation Guidance
- Add: `tests/unit/inspect_agents/test_retry_and_cache.py`
- Use provider: `mockllm` with `custom_outputs` callable passed via `get_model(..., custom_outputs=...)`. 〖F:external/inspect_ai/src/inspect_ai/model/_providers/mockllm.py†L13-L36〗
- Build path: Use `build_supervisor` with model set to `mockllm/model`, plus the new args from Features 1–2.
- Utilities: `src/inspect_agents/run.py::run_agent()` to execute an Agent. 〖F:src/inspect_agents/run.py†L6-L26〗
- Greppable identifiers: `mockllm`, `custom_outputs`, `Model.should_retry`, `ModelOutput.for_tool_call`, `build_supervisor(`.

Test 1 — Retry on transient error
1) Define `class TransientError(Exception): pass`.
2) Monkeypatch `inspect_ai.model._model.Model.should_retry` to return `isinstance(ex, TransientError)`.
3) Create `calls=[0]` and `def outputs(input, tools, tool_choice, config):`:
   - On first call: `calls[0]+=1`; `raise TransientError()`.
   - On second call: `calls[0]+=1`; return `ModelOutput.for_tool_call(model="mockllm", tool_name="submit", tool_arguments={"answer":"OK"})`. 〖F:external/inspect_ai/src/inspect_ai/model/_model_output.py†L236-L268〗
4) Build supervisor with `max_retries=1` (and `cache=False`).
5) Run with `asyncio.run(run_agent(agent, "hello"))`.
6) Assert completion contains `OK` and `calls[0] == 2`.

Test 2 — Cache reuse
1) Create `calls=[0]` and `def outputs(...): calls[0]+=1; return ModelOutput.for_tool_call(..., {"answer":"CACHED"})`.
2) Build supervisor with `cache=True` (or a `CachePolicy(expiry="1D", per_epoch=False)`).
3) Execute two identical runs (fresh Agent state each time).
4) Assert both completions are `CACHED` and `calls[0] == 1` (second run served from cache).
5) Optionally verify transcript recorded `cache="read"` on second call by inspecting ModelEvent if accessible. 〖F:external/inspect_ai/src/inspect_ai/model/_model.py†L641-L647〗

Test Settings
- Env: `CI=1`, `NO_NETWORK=1`, `PYTHONPATH=src:external/inspect_ai`.
- Keep tests isolated; do not import or modify approval chain suites.

Success Criteria
- Retry test passes: one transient failure then success; `calls==2`.
- Cache test passes: second identical run hits cache; `calls==1`.
- Tests run offline/deterministic.

Task Checklist
- [ ] Add test file `tests/unit/inspect_agents/test_retry_and_cache.py`.
- [ ] Implement transient error retry test using `mockllm` and monkeypatch.
- [ ] Implement cache reuse test with identical inputs and assert the provider callable invoked once.
- [ ] Ensure tests set `NO_NETWORK=1` and run under `CI=1`.
- [ ] Keep cache disabled in other suites; only enable within this test file.

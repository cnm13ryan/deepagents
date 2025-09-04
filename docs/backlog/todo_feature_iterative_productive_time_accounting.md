# TODO: Iterative Agent — Productive-Time Accounting (subtract provider retry/backoff)

Status: DONE (2025-09-04)
- Implemented via `generate_with_retry_time` helper and integrated in the iterative loop, subtracting provider retry/backoff from the time budget and logging progress metrics.
  - Code: `src/inspect_agents/_model_retry.py`, `src/inspect_agents/iterative.py` (accumulation, timeouts, logs).
- Tests: see `tests/unit/inspect_agents/iterative/test_iterative_productive_time.py` for step count and progress logging assertions.

## Context & Motivation
- Purpose: Count only productive model time against the agent’s wall-clock budget by subtracting provider retry/backoff delays. This prevents long rate-limit backoffs from stealing work time.
- Problem: The iterative loop exits based on raw wall-clock elapsed; any provider retries reduce useful work time. Aligns with PaperBench semantics (subtracts retry time) while staying Inspect-native.
- Value: More predictable runtimes across models/providers; better utilization of the allotted time window.
- Constraints: Avoid monkey-patching Inspect; keep behavior opt-in via env flag (default off) to preserve current semantics.

## Implementation Guidance
- Examine:
  - `src/inspect_agents/iterative.py` — loop time budget and per-call timeout.
    - Grep: `def build_iterative_agent(`, `elapsed = time.time() - start`, `GenerateConfig(timeout=`.
  - New helper module (suggested): `src/inspect_agents/_retry_time.py` — a thin wrapper for model `.generate()` that tracks retry/backoff time.
- Approach:
  1) Implement `generate_with_retry_time(model, *, input, tools, cache, config) -> tuple[Output, float]`:
     - Wrap `model.generate(...)` with `tenacity` (retry on transient provider exceptions you already handle elsewhere).
     - In `before_sleep(retry_state)`, accumulate `retry_state.next_action.sleep` into a local counter.
     - Return `(output, total_retry_s)` so caller can add to a loop-local `total_retry_time`.
  2) In `iterative.py` loop:
     - Track `total_retry_time = 0.0` from the start.
     - Replace direct `model_obj.generate(...)` with the wrapper; add the returned retry seconds to `total_retry_time`.
     - Change time checks and timeouts to subtract retry time:
       ```python
       # Before: elapsed = time.time() - start
       productive_elapsed = (time.time() - start) - total_retry_time
       if _time_limit is not None and productive_elapsed >= _time_limit:
           break
       # Timeout for generate and tools
       remaining = int(_time_limit - productive_elapsed)
       gen_timeout = max(1, remaining) if remaining > 0 else 1
       ```
  - Logging: every `progress_every` steps, log `elapsed`, `total_retry_time`, and `productive_elapsed`.
- Greppable identifiers in `iterative.py` to anchor changes:
  - `while True:` main loop
  - `elapsed = time.time() - start`
  - `GenerateConfig(timeout=gen_timeout)`
  - `async with asyncio.timeout(timeout_ctx):` (tools section)
- Dependencies:
  - `tenacity` for retries; reuse existing exception types your providers raise (rate limit, timeouts, 5xx).

## Scope Definition
- Implement in the iterative agent only (`build_iterative_agent`).
- Keep behind env flag `INSPECT_PRODUCTIVE_TIME=1` (and/or function arg) to enable; default remains wall-clock accounting.
- Do not alter the submit-style supervisor agent.

## Success Criteria
- Behavior:
  - With simulated backoffs totaling ~120s and `real_time_limit_sec=600`, the agent should achieve ~600s of productive steps (vs. ~480s before) when the flag is enabled.
  - Progress logs include `productive_elapsed` and `total_retry_time` fields.
- Testing:
  - Add a stub model whose `generate` fails N times with controlled sleep before succeeding; assert the loop allows more steps with productive-time enabled.
  - Unit test timeouts: computed `gen_timeout` never negative and decreases to 1s when near budget.
- Compatibility:
  - If the wrapper can’t detect retryable exceptions, fall back to current behavior without breaking the loop.

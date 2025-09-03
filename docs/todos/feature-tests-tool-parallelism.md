# TODO — Test Suite Updates for Tool Parallelism Policy

Status: Planned • Owner: TBA • Priority: High

## Context & Motivation
- Purpose: Verify the new policy end‑to‑end and prevent regressions.
- Problem: Current “handoff + other tool” case is xfail; multi‑handoff behavior and kill‑switch are not tested.
- User impact: Stable, predictable behavior; early detection of concurrency regressions.

## Implementation Guidance
- File(s) to modify: `tests/integration/inspect_agents/test_parallel.py`
- Update / add tests:
  1) Remove xfail from `test_handoff_with_other_tool_only_handoff_executes` after exclusivity is implemented.
  2) Add multi‑handoff test: first handoff wins; others are skipped (assert via transcript ToolEvents with `error.code=="skipped"`).
  3) Add kill‑switch test: set `INSPECT_DISABLE_TOOL_PARALLEL=1`; confirm the execution path disables parallel tool calls (assert via behavior/logs or config path if feasible in harness).
  4) Keep the baseline: two simple parallel‑safe tools both execute and yield messages (document no ordering guarantee).
- Greppable anchors: `execute_tools(`, `_tool(` helper, `build_subagents(`, `transcript()`.
- Related deps: `inspect_ai.log._transcript` for reading ToolEvents; `inspect_ai.tool` classes for message typing.

## Scope Definition
- In scope: Integration tests only; do not modify production logic here.
- Focus: conversation messages for executed tools; transcript “skipped” events for gated calls; env flag behavior.
- Avoid: Provider/network dependencies (use NO_NETWORK and mock/none providers as appropriate).

## Success Criteria
- All tool parallelism tests pass without xfail once features land.
- Baseline two‑tool concurrency remains intact; handoff exclusivity is enforced.
- Transcript assertions for `skipped` ToolEvents are reliable and deterministic.

---

### Checklist
- [ ] Enable/adjust the handoff+echo test to assert exclusivity (remove xfail).
- [ ] Add a multi‑handoff test; assert first‑wins policy and transcript `skipped` events for others.
- [ ] Add a kill‑switch test for `INSPECT_DISABLE_TOOL_PARALLEL=1`.
- [ ] Keep/validate the two‑parallel‑tools test.


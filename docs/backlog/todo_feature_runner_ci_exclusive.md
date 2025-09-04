# TODO: Research Runner — Apply Handoff Exclusivity in CI

Status: DONE (2025-09-04)
- Implemented in `examples/research/run_local.py`: when `--approval` is provided, the runner extends the chosen preset (`ci|dev|prod`) with `handoff_exclusive_policy()` so CI runs enforce “first handoff wins”.
- Presets: `approval_preset("ci")` remains permissive by design; the runner’s explicit extension ensures CI exclusivity without changing preset semantics.
- Tests: see `tests/integration/research/test_run_local_exclusive_ci.py`.

## Context & Motivation
- Purpose: reduce flakiness in automation by ensuring only one handoff executes per turn in the example runner when `--approval ci` is used.
- Problem: `ci` preset currently approves all; exclusivity added only for dev/prod in the runner.
- Value: deterministic example behavior in CI pipelines.

## Implementation Guidance
- Examine: `examples/research/run_local.py` (approval flags & policy composition).
- Grep tokens: `--approval`, `approval_preset(args.approval)`, `handoff_exclusive_policy()`.

## Scope Definition
- Implement: append `handoff_exclusive_policy()` when `args.approval == "ci"`; optionally gate with `--ci-exclusive/--no-ci-exclusive` (default on).
- Tests: toy model with two handoffs -> assert only one executes under `ci`.

## Success Criteria
- Behavior: CI runs show single handoff result.
- Docs: runner help updated to describe the flag/behavior.

# TODO: Research Runner — Apply Handoff Exclusivity in CI

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

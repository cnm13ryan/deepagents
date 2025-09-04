# TODO: Approvals Presets — Add Handoff Exclusivity by Default (dev/prod)

Status: DONE (2025-09-04)
- Implemented: `approval_preset("dev"|"prod")` returns an ordered policy chain via `approval_chain(...)` that prepends `handoff_exclusive_policy()` and the parallel kill-switch when enabled.
  - Code: `src/inspect_agents/approval.py` (`approval_preset`, `approval_chain`, `handoff_exclusive_policy`).
- Tests: see `tests/integration/inspect_agents/test_handoff_exclusive_end_to_end.py` and `tests/integration/inspect_agents/test_handoff_exclusivity_integration.py`.

## Context & Motivation
- Purpose: ship safer defaults so only one sub‑agent handoff executes per assistant turn in developer and production runs.
- Problem: `approval_preset("dev"|"prod")` doesn’t include the exclusivity approver; examples add it manually. This surprises users with multiple handoffs executing in parallel.
- Value: predictable transcripts, fewer race conditions, better parity with ADR 0005.
- Constraints: keep `ci` preset permissive unless explicitly extended; no API breaking changes.

## Implementation Guidance
- Examine: `src/inspect_agents/approval.py` (preset logic and `handoff_exclusive_policy()`), `docs/how-to/approvals.md`, `examples/research/run_local.py` (shows current manual append).
- Grep tokens: `approval_preset(`, `case "dev"`, `case "prod"`, `handoff_exclusive_policy(`.
- Pattern (current):
  ```py
  match preset:
      case "ci":
          return [ApprovalPolicy(approver=approve_all, tools="*")]
      case "dev":
          return [ApprovalPolicy(approver=dev_gate, tools="*"), ApprovalPolicy(approver=reject_all, tools="*")]
      case "prod":
          return [ApprovalPolicy(approver=prod_gate, tools="*")]
  ```

## Scope Definition
- Implement: include `handoff_exclusive_policy()` in the lists returned for `dev` and `prod` presets.
- Do not change: `ci` preset behavior.
- Update docs: approvals how‑to to note exclusivity is on by default for dev/prod; remove manual append from example runner.

## Success Criteria
- Behavior: calling `approval_preset("dev")` or `("prod")` returns a list that includes the exclusivity approver and enforces “first handoff wins”.
- Tests: add/extend unit tests asserting exactly one handoff is approved and others are rejected with explanation “Skipped due to handoff exclusivity”. Run `uv run pytest -q -k handoff_exclusive_policy`.
- Compatibility: examples continue to work without appending the policy manually.

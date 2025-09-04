# TODO: Token‑Aware Pruning (Optional)

## Context & Motivation
- Purpose: reduce overflow by capping tokens rather than message count when Inspect utilities are present.
- Problem: length‑based pruning can be suboptimal near provider limits.
- Value: smoother behavior near context limits; fewer retries.
- Constraints: keep provider‑agnostic; soft dependency only.

## Implementation Guidance
- Examine: `src/inspect_agents/iterative.py` (prune strategy integration), `src/inspect_agents/_conversation.py` (keep as is), Inspect token utilities if available.
- Grep tokens: `prune_messages(`, `IndexError`/`model_length` overflow, `INSPECT_PRUNE_TOKEN_BUDGET` (to add).

## Scope Definition
- Implement: strategy switch via `INSPECT_PRUNE_STRATEGY=token|length` and `INSPECT_PRUNE_TOKEN_BUDGET=<int>`; when `token`, approximate tokens and trim oldest non‑system/first‑user while preserving tool pairings; else use current length strategy.
- Avoid: provider‑specific libs; fail open to length if utilities unavailable.
- Tests: stub token estimator to validate trimming under a token budget.

## Success Criteria
- Behavior: with strategy=token, messages kept satisfy budget approximation; defaults unchanged.
- Tests: deterministic offline tests pass.
- Docs: add a note marking token strategy as best‑effort.

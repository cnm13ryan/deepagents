# TODO: Iterative Agent — Add `max_messages`

## Context & Motivation
- Purpose: expose a hard cap by messages in addition to `max_turns`.
- Problem: current heuristic keeps ~`2*max_turns` messages; users may prefer explicit cap.
- Value: predictable memory/cost control; clearer semantics.

## Implementation Guidance
- Examine: `src/inspect_agents/iterative.py` (builder signature, `_prune_history`).
- Grep tokens: `def build_iterative_agent(`, `_prune_history(`, `max_turns`.

## Scope Definition
- Implement: add `max_messages: int | None = None`; in `_prune_history`, when set, prefer it to cap the tail after preserving all system + first user and tool pairings.
- Preserve: existing default `max_turns=50`; document precedence.
- Tests: param tests ensure preserved prefixes and tool pairing under various caps.

## Success Criteria
- Behavior: tail length respects `max_messages` when provided; default unchanged.
- Tests: new unit tests pass.

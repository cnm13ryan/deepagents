# Testing Guide — Property-Based (Hypothesis)

Use Hypothesis to stress contracts (e.g., schema classifiers, env parsing, pruning invariants).

## Patterns
- Basic: `@given(...)` with strategies for inputs; assert invariants (idempotence, monotonicity, classification stability).
- Health checks: keep data small, add deadlines or `@settings(deadline=None)` judiciously to avoid flakiness.
- Determinism: pin Hypothesis seed in CI via env if needed.

## Targets
- `classify_tool_arg_error`: build messages that match error classes and assert stable code mapping.
- `_conversation.prune_messages`: ensure preserved invariants (system and first user kept; tail size bound; tool pairing honored).

## References
- Hypothesis docs and strategies.

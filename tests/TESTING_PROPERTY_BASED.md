# Testing Guide — Property-Based (Hypothesis)

Use Hypothesis to stress contracts (e.g., schema classifiers, env parsing, pruning invariants).

## Patterns
- Basic: `@given(...)` with strategies for inputs; assert invariants (idempotence, monotonicity, classification stability).
- Health checks: keep data small, add deadlines or `@settings(deadline=None)` judiciously to avoid flakiness.
- Determinism: pin Hypothesis seed in CI via env if needed.

## Targets
- `classify_tool_arg_error`: build messages that match error classes and assert stable code mapping.
- `_conversation.prune_messages`: ensure preserved invariants (system and first user kept; tail size bound; tool pairing honored).

## Examples
- Classifier stability for schema errors:
  ```python
  from hypothesis import given, strategies as st
  from inspect_agents.schema import classify_tool_arg_error, ErrorCode

  @given(st.one_of(
      st.just("required property missing"),
      st.just("Value is not of type string"),
      st.just("Additional properties are not allowed"),
      st.just("Error parsing: invalid"),
  ))
  def test_classify_tool_arg_error_stable(msg):
      code = classify_tool_arg_error(msg)
      assert code in {"MISSING_REQUIRED","TYPE_MISMATCH","EXTRA_FIELD","PARSING_ERROR","UNKNOWN_SCHEMA_ERROR"}
  ```
## References
- Hypothesis docs and strategies.

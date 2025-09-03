# DONE — Tool Argument Schema & Errors

Context & Motivation
- Provide predictable, developer-friendly errors for invalid tool arguments; leverage Inspect’s JSON Schema validation and YAML parsing.

Implementation Guidance
- Validation: `validate_tool_input` and ToolParams in `external/inspect_ai/src/inspect_ai/model/_call_tools.py`
- YAML/coercion path: `parse_tool_call`

Scope — Do
- [x] Define stable error codes/phrases for schema violations (see `inspect_agents.schema.classify_tool_arg_error`)
- [x] Tests cover: missing required, wrong types, extra fields, YAML coercion edge cases
- [x] Document expected error surface and guidance for fixing calls

Scope — Don’t
- Don’t assert full error strings in tests; match on codes/phrases

Success Criteria
- [x] Invalid inputs produce consistent, actionable messages; tests pass (see `tests/unit/inspect_agents/test_tool_schema.py`)

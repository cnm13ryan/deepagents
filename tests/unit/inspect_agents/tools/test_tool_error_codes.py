from inspect_agents.schema import classify_tool_arg_error


def test_missing_required_code_matches_both_sources():
    msg_jsonschema = "Found 1 validation errors parsing tool input arguments:\n- 'b' is a required property"
    msg_toolparam = "Required parameter b not provided to tool call."
    assert classify_tool_arg_error(msg_jsonschema) == "MISSING_REQUIRED"
    assert classify_tool_arg_error(msg_toolparam) == "MISSING_REQUIRED"


def test_type_mismatch_code_matches_both_sources():
    msg_jsonschema = "'oops' is not of type 'number'"
    msg_toolparam = "Unable to convert 'oops' to float"
    assert classify_tool_arg_error(msg_jsonschema) == "TYPE_MISMATCH"
    assert classify_tool_arg_error(msg_toolparam) == "TYPE_MISMATCH"


def test_extra_field_code_matches():
    msg = "Additional properties are not allowed ('c' was unexpected)"
    assert classify_tool_arg_error(msg) == "EXTRA_FIELD"


def test_unknown_and_parsing_codes():
    assert classify_tool_arg_error(None) == "UNKNOWN_SCHEMA_ERROR"
    assert (
        classify_tool_arg_error(
            "Error parsing the following tool call arguments:\n\n{bad}\n\nError details: ..."
        )
        == "PARSING_ERROR"
    )


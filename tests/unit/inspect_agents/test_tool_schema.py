import asyncio

from inspect_ai.model._call_tools import execute_tools, parse_tool_call
from inspect_agents.schema import classify_tool_arg_error
from inspect_ai.model._chat_message import (
    ChatMessageAssistant,
    ChatMessageTool,
    ChatMessageUser,
)
from inspect_ai.tool._tool_def import ToolDef
from inspect_ai.tool._tool_info import parse_tool_info
from inspect_ai.tool._tool_params import ToolParams
from inspect_ai.util._json import json_schema


def _sum_tool():
    async def execute(a: float, b: float) -> float:
        return a + b

    params = ToolParams()
    params.properties["a"] = json_schema(float)
    params.properties["a"].description = "first addend"  # type: ignore[index]
    params.properties["b"] = json_schema(float)
    params.properties["b"].description = "second addend"  # type: ignore[index]
    params.required = ["a", "b"]
    return ToolDef(
        execute,
        name="sum_two",
        description="Sum two numbers",
        parameters=params,
    ).as_tool()


def _assistant_with_call(function: str, arguments: dict):
    return ChatMessageAssistant(
        content="",
        tool_calls=[dict(id="1", function=function, arguments=arguments)],
    )


def test_missing_required_field_yields_parsing_error_phrase():
    # JSON Schema phrasing (simulated) — stable phrase check via classifier
    msg = "Found 1 validation errors parsing tool input arguments:\n- 'b' is a required property"
    assert classify_tool_arg_error(msg) == "MISSING_REQUIRED"


def test_wrong_type_yields_parsing_error_phrase():
    # Integration path via tool_param coercion
    tool = _sum_tool()
    msgs = [
        ChatMessageUser(content="go"),
        _assistant_with_call("sum_two", {"a": "oops", "b": 2}),
    ]
    result = asyncio.run(execute_tools(msgs, [tool]))
    tool_msg = next(m for m in result.messages if isinstance(m, ChatMessageTool))
    assert tool_msg.error is not None and tool_msg.error.type == "parsing"
    assert "Unable to convert" in tool_msg.error.message
    assert classify_tool_arg_error(tool_msg.error.message) == "TYPE_MISMATCH"


def test_extra_field_yields_additional_properties_phrase():
    # Simulated JSON Schema message — validated via classifier
    msg = "Found 1 validation errors parsing tool input arguments:\n- Additional properties are not allowed ('c' was unexpected)"
    assert classify_tool_arg_error(msg) == "EXTRA_FIELD"


def _echo_first_param_tool():
    async def execute(value: float) -> float:
        return value

    params = ToolParams()
    params.properties["value"] = json_schema(float)
    params.properties["value"].description = "value to echo"  # type: ignore[index]
    params.required = ["value"]
    return ToolDef(
        execute,
        name="echo_value",
        description="Echo first param (float)",
        parameters=params,
    ).as_tool()


def test_yaml_coercion_maps_scalar_to_first_param():
    tool = _echo_first_param_tool()
    tool_info = parse_tool_info(tool)
    call = parse_tool_call(id="1", function="echo_value", arguments="42", tools=[tool_info])
    assert call.arguments == {"value": 42}

    call_true = parse_tool_call(id="2", function="echo_value", arguments="true", tools=[tool_info])
    assert call_true.arguments == {"value": True}

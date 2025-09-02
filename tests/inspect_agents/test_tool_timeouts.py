import asyncio

import anyio

from inspect_ai.agent._agent import AgentState
from inspect_ai.model._chat_message import ChatMessageAssistant, ChatMessageUser
from inspect_ai.tool._tool_call import ToolCall
from inspect_ai.model._call_tools import execute_tools
from inspect_ai.tool._tool import tool, Tool
from inspect_ai.tool._tool_params import ToolParams
from inspect_ai.tool._tool_def import ToolDef


def slow_tool() -> Tool:  # type: ignore[return-type]
    async def execute(delay: float = 1.0, timeout: float = 0.01) -> str:
        with anyio.move_on_after(timeout) as scope:
            await anyio.sleep(delay)
        if scope.cancel_called:
            raise TimeoutError("tool timed out")
        return "done"

    # Manually define params to satisfy schema/description requirements
    params = ToolParams()
    # Use JSON schema helper to produce proper ToolParam entries
    from inspect_ai.util._json import json_schema
    params.properties["delay"] = json_schema(float)
    params.properties["delay"].description = "seconds to sleep"  # type: ignore[index]
    params.properties["delay"].default = 1.0  # type: ignore[index]
    params.properties["timeout"] = json_schema(float)
    params.properties["timeout"].description = "timeout seconds before raising"  # type: ignore[index]
    params.properties["timeout"].default = 0.01  # type: ignore[index]

    return ToolDef(
        execute,
        name="slow_tool",
        description="Simulate long-running tool for timeout testing",
        parameters=params,
    ).as_tool()


def _conv_with_tool():
    return [
        ChatMessageUser(content="start"),
        ChatMessageAssistant(
            content="",
            tool_calls=[
                ToolCall(
                    id="1",
                    function="slow_tool",
                    arguments={"delay": 2.0, "timeout": 0.01},
                )
            ],
        ),
    ]


def test_timeout_surfaces_tool_error_and_transcript():
    messages = _conv_with_tool()
    result = asyncio.run(execute_tools(messages, [slow_tool()]))
    tool_msg = result.messages[0]
    # Tool message should carry a timeout error
    assert getattr(tool_msg, "error", None) is not None
    assert tool_msg.error.type == "timeout"

    # Transcript should have a ToolEvent whose error is timeout as well
    from inspect_ai.log._transcript import transcript, ToolEvent

    # Use helper to fetch the last ToolEvent
    ev = transcript().find_last_event(ToolEvent)
    assert ev is not None

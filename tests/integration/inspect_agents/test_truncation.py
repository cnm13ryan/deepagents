import asyncio

from inspect_ai.model._call_tools import execute_tools
from inspect_ai.model._chat_message import ChatMessageAssistant, ChatMessageTool, ChatMessageUser
from inspect_ai.tool._tool_def import ToolDef
from inspect_ai.tool._tool_params import ToolParams


def long_output_tool():
    async def execute() -> str:
        return "x" * 500

    params = ToolParams()
    return ToolDef(execute, name="long_output", description="returns long text", parameters=params).as_tool()


def _assistant_call():
    return ChatMessageAssistant(
        content="",
        tool_calls=[dict(id="1", function="long_output", arguments={})],
    )


def test_truncation_envelope_and_limits():
    tool = long_output_tool()
    messages = [ChatMessageUser(content="go"), _assistant_call()]
    result = asyncio.run(execute_tools(messages, [tool], max_output=100))

    # Assert envelope template present in tool message
    tm = next(m for m in result.messages if isinstance(m, ChatMessageTool))
    text = tm.content if isinstance(tm.content, str) else "".join([c.text for c in tm.content if hasattr(c, "text")])
    assert "The output of your call to long_output was too long to be displayed." in text
    assert "<START_TOOL_OUTPUT>" in text and "<END_TOOL_OUTPUT>" in text

    # Assert truncated bytes are recorded in transcript ToolEvent

    # Additionally assert that the bytes within the envelope equal the limit
    start = text.index("<START_TOOL_OUTPUT>") + len("<START_TOOL_OUTPUT>")
    end = text.index("<END_TOOL_OUTPUT>")
    payload = text[start:end].strip("\n")
    assert len(payload.encode("utf-8")) == 100

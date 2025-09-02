import asyncio

from inspect_ai.model._chat_message import (
    ChatMessageAssistant,
    ChatMessageTool,
    ChatMessageUser,
)
from inspect_ai.tool._tool_def import ToolDef, tool_defs
from inspect_ai.tool._tool_params import ToolParams
from inspect_ai.model._call_tools import execute_tools
from inspect_ai.tool._tool import Tool

from inspect_agents.agents import build_subagents


def _tool(name: str, reply: str) -> Tool:
    async def execute() -> str:
        return reply

    params = ToolParams()
    return ToolDef(execute, name=name, description=f"Return {reply}", parameters=params).as_tool()


def _conv_two_calls(fn1: str, fn2: str):
    return [
        ChatMessageUser(content="start"),
        ChatMessageAssistant(
            content="",
            tool_calls=[
                dict(id="1", function=fn1, arguments={}),
                dict(id="2", function=fn2, arguments={}),
            ],
        ),
    ]


def test_two_parallel_tools_both_execute():
    t1 = _tool("echo_a", "A")
    t2 = _tool("echo_b", "B")

    messages = _conv_two_calls("echo_a", "echo_b")
    result = asyncio.run(execute_tools(messages, [t1, t2]))
    tool_msgs = [m for m in result.messages if isinstance(m, ChatMessageTool)]
    funcs = [m.function for m in tool_msgs]
    assert set(funcs) == {"echo_a", "echo_b"}


def test_handoff_tool_declares_serial_execution():
    # Build a single subagent handoff tool
    tools = build_subagents(
        configs=[
            dict(
                name="reader",
                description="Reads stuff",
                prompt="Reply",
            )
        ],
        base_tools=[],
    )
    handoff_tool = tools[0]

    # Extract ToolDef and assert parallel flag is False (serial)
    defs = asyncio.run(tool_defs([handoff_tool]))
    assert len(defs) == 1
    assert defs[0].parallel is False


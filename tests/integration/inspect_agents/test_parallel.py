import asyncio
import os

import pytest
from inspect_ai.agent._agent import Agent, AgentState
from inspect_ai.agent._agent import agent as agent_dec
from inspect_ai.agent._handoff import handoff
from inspect_ai.model._call_tools import execute_tools
from inspect_ai.model._chat_message import (
    ChatMessageAssistant,
    ChatMessageTool,
    ChatMessageUser,
)
from inspect_ai.tool._tool import Tool
from inspect_ai.tool._tool_def import ToolDef, tool_defs
from inspect_ai.tool._tool_params import ToolParams
from inspect_ai.util._limit import time_limit

from inspect_agents.agents import build_subagents

pytestmark = pytest.mark.parallel


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
                model="mockllm/model",
                limits=[time_limit(0.01)],
            )
        ],
        base_tools=[],
    )
    handoff_tool = tools[0]

    # Extract ToolDef and assert parallel flag is False (serial)
    defs = asyncio.run(tool_defs([handoff_tool]))
    assert len(defs) == 1
    assert defs[0].parallel is False


@pytest.mark.xfail(reason="Handoff should cancel/skip other tool calls in same turn")
def test_handoff_with_other_tool_only_handoff_executes():
    # Simple parallel-safe echo tool
    echo = _tool("echo_b", "B")

    # Tiny no-model agent that returns immediately, wrapped as a handoff tool
    @agent_dec(name="reader", description="Reads stuff")
    def simple_agent() -> Agent:  # pragma: no cover
        async def _run(state: AgentState) -> AgentState:
            return state

        return _run

    agent = simple_agent()

    handoff_tool = handoff(
        agent,
        description="Reads stuff",
        tool_name="transfer_to_reader",
        limits=[time_limit(0.01)],
    )

    # Assistant calls both the handoff tool and a normal tool
    messages = [
        ChatMessageUser(content="start"),
        ChatMessageAssistant(
            content="",
            tool_calls=[
                dict(id="1", function="transfer_to_reader", arguments={}),
                dict(id="2", function="echo_b", arguments={}),
            ],
        ),
    ]

    # Execute with both tools available
    os.environ.setdefault("INSPECT_EVAL_MODEL", "mockllm/model")
    result = asyncio.run(execute_tools(messages, [handoff_tool, echo]))

    # Only the handoff should be satisfied; echo_b should NOT run
    tool_msgs = [m for m in result.messages if isinstance(m, ChatMessageTool)]
    funcs = [m.function for m in tool_msgs]

    assert "transfer_to_reader" in funcs
    assert "echo_b" not in funcs

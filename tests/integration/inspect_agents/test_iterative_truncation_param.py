import asyncio

import pytest
from inspect_ai.model._chat_message import ChatMessageAssistant, ChatMessageSystem, ChatMessageUser
from inspect_ai.model._model import Model
from inspect_ai.model._model_output import ModelOutput
from inspect_ai.tool._tool_def import ToolDef
from inspect_ai.tool._tool_params import ToolParams

from inspect_agents.iterative import build_iterative_agent

pytestmark = pytest.mark.truncation


def long_output_tool():
    async def execute() -> str:
        # Return an output well above 10 KiB to exercise truncation
        return "x" * (20 * 1024)

    params = ToolParams()
    return ToolDef(execute, name="long_output", description="returns long text", parameters=params).as_tool()


class OneCallToolModel(Model):
    async def generate(self, input, tools, config, cache: bool = False):
        # Always request our long_output tool
        return ModelOutput.from_message(
            ChatMessageAssistant(
                content="",
                tool_calls=[{"id": "1", "function": "long_output", "arguments": {}}],
                source="generate",
            )
        )


def _run(agent, state):
    return asyncio.run(agent(state))


def test_iterative_param_caps_tool_output(monkeypatch):
    # Ensure env does not interfere; rely on explicit param precedence
    monkeypatch.delenv("INSPECT_MAX_TOOL_OUTPUT", raising=False)

    # Build agent with explicit 4 KiB cap passed as parameter
    tool = long_output_tool()
    agent = build_iterative_agent(
        model=OneCallToolModel.__new__(OneCallToolModel),
        tools=[tool],
        max_steps=1,
        max_tool_output_bytes=4096,
    )

    # Seed conversation with a system + user
    from inspect_ai.agent._agent import AgentState

    state = AgentState(messages=[ChatMessageSystem(content="sys"), ChatMessageUser(content="start")])

    new_state = _run(agent, state)

    # Locate tool message
    from inspect_ai.model._chat_message import ChatMessageTool

    tool_msgs = [m for m in new_state.messages if isinstance(m, ChatMessageTool)]
    assert tool_msgs, "Expected a tool message from long_output"

    tm = tool_msgs[0]
    # Tool content can be a string or list of Content; normalize to text
    if isinstance(tm.content, str):
        text = tm.content
    else:
        text = "".join([getattr(c, "text", "") for c in tm.content])

    # Assert envelope present and payload length equals the configured cap
    assert "The output of your call to long_output was too long to be displayed." in text
    assert "<START_TOOL_OUTPUT>" in text and "<END_TOOL_OUTPUT>" in text

    start = text.index("<START_TOOL_OUTPUT>") + len("<START_TOOL_OUTPUT>")
    end = text.index("<END_TOOL_OUTPUT>")
    payload = text[start:end].strip("\n")
    assert len(payload.encode("utf-8")) == 4096

import asyncio
from typing import Any

from inspect_ai.agent._agent import AgentState
from inspect_ai.model._chat_message import (
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageUser,
)
from inspect_ai.model._model import Model
from inspect_ai.model._model_output import ModelOutput
from inspect_ai.tool._tool_def import ToolDef
from inspect_ai.tool._tool_params import ToolParams

from inspect_agents.iterative import build_iterative_agent


class NoToolModel(Model):
    async def generate(self, input, tools, config, cache: bool = False):  # noqa: ARG002
        return ModelOutput.from_message(
            ChatMessageAssistant(content="ok", source="generate")
        )


def test_clock_injection_constant_zero_formats_progress_zero():
    # Arrange: constant clock -> elapsed always 0; progress message should reflect 00:00:00
    agent = build_iterative_agent(
        model=NoToolModel.__new__(NoToolModel),
        max_steps=2,
        progress_every=1,
        clock=lambda: 0.0,
    )

    state = AgentState(messages=[ChatMessageSystem(content="sys"), ChatMessageUser(content="start")])

    # Act
    new_state = asyncio.run(agent(state))

    # Assert: last Info message shows zero elapsed
    infos = [m for m in new_state.messages if isinstance(m, ChatMessageUser) and isinstance(m.content, str) and m.content.startswith("Info: ")]
    assert infos, "Expected at least one progress Info message"
    assert any("00:00:00 elapsed" in (m.content or "") for m in infos)


def noop_tool():
    async def execute() -> str:
        return "ok"

    return ToolDef(execute, name="noop", description="returns ok", parameters=ToolParams()).as_tool()


class ToolModel(Model):
    async def generate(self, input, tools, config, cache: bool = False):  # noqa: ARG002
        # Always request the noop tool
        return ModelOutput.from_message(
            ChatMessageAssistant(
                content="",
                tool_calls=[{"id": "1", "function": "noop", "arguments": {}}],
                source="generate",
            )
        )


def test_timeout_factory_injection_observes_remaining_budget():
    # Capture timeout values the agent passes to the factory
    calls: list[int] = []

    class DummyTimeout:
        def __init__(self, v: int):
            self.v = v

        async def __aenter__(self) -> None:  # record on enter
            calls.append(int(self.v))
            return None

        async def __aexit__(self, exc_type, exc, tb) -> bool:  # noqa: D401, ARG002
            return False

    def factory(v: int) -> Any:
        return DummyTimeout(v)

    # Constant clock keeps elapsed at 0 so remaining == time limit
    tool = noop_tool()
    agent = build_iterative_agent(
        model=ToolModel.__new__(ToolModel),
        tools=[tool],
        max_steps=1,
        real_time_limit_sec=7,
        clock=lambda: 0.0,
        timeout_factory=factory,
    )

    state = AgentState(messages=[ChatMessageSystem(content="sys"), ChatMessageUser(content="start")])
    _ = asyncio.run(agent(state))

    assert calls, "Expected timeout_factory to be invoked for tool execution"
    assert calls[0] == 7, f"Expected remaining budget 7, got {calls[0]}"


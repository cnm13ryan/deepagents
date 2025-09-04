import asyncio
from typing import Any

from inspect_ai.model._model import Model

from inspect_agents.iterative import build_iterative_agent


class TinyModel(Model):
    async def generate(self, input, tools, config, cache: bool = False):
        from inspect_ai.model._chat_message import ChatMessageAssistant
        from inspect_ai.model._model_output import ModelOutput

        return ModelOutput.from_message(ChatMessageAssistant(content="ok", source="generate"))


def _dummy_model() -> Model:
    # Bypass Model.__init__; our override doesn't use base state
    return TinyModel.__new__(TinyModel)


def _run(agent, state):
    return asyncio.run(agent(state))


def _make_messages(n_tail: int) -> list[Any]:
    # Build [System, User] + n_tail Assistant messages
    from inspect_ai.model._chat_message import (
        ChatMessageAssistant,
        ChatMessageSystem,
        ChatMessageUser,
    )

    msgs: list[Any] = [ChatMessageSystem(content="sys"), ChatMessageUser(content="start")]
    msgs.extend(ChatMessageAssistant(content=f"A{i}") for i in range(n_tail))
    return msgs


def test_soft_stop_message_limit_triggers_and_notes_reason():
    from inspect_ai.agent._agent import AgentState
    from inspect_ai.model._chat_message import ChatMessageUser

    # Arrange: prepare exactly N existing messages; limit == len(messages)
    msgs = _make_messages(10)
    limit = len(msgs)
    state = AgentState(messages=msgs)

    agent = build_iterative_agent(
        model=_dummy_model(),
        max_steps=50,
        message_limit=limit,
    )

    # Act
    new_state = _run(agent, state)

    # Assert: final message explains the stop and no extra assistant was generated
    assert isinstance(new_state.messages[-1], ChatMessageUser)
    assert "[limit] Message limit reached" in (new_state.messages[-1].content or "")


def test_soft_stop_token_limit_triggers_and_notes_reason():
    from inspect_ai.agent._agent import AgentState
    from inspect_ai.model._chat_message import ChatMessageSystem, ChatMessageUser

    # Arrange: a long user message that will exceed a tiny token_limit
    long_text = "x" * 200  # heuristic ~50 tokens (> token_limit)
    msgs = [ChatMessageSystem(content="sys"), ChatMessageUser(content=long_text)]
    state = AgentState(messages=msgs)

    agent = build_iterative_agent(
        model=_dummy_model(),
        max_steps=50,
        token_limit=20,  # small to trigger immediately
    )

    # Act
    new_state = _run(agent, state)

    # Assert: final message explains the token stop
    assert isinstance(new_state.messages[-1], ChatMessageUser)
    assert "[limit] Token limit reached" in (new_state.messages[-1].content or "")


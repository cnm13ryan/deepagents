import asyncio
import logging
from typing import Any

from inspect_ai.model._model import Model

from inspect_agents.iterative import build_iterative_agent


class TinyModel(Model):
    async def generate(self, input, tools, config, cache: bool = False):
        from inspect_ai.model._chat_message import ChatMessageAssistant
        from inspect_ai.model._model_output import ModelOutput

        return ModelOutput.from_message(ChatMessageAssistant(content="ok", source="generate"))


def dummy_model() -> Model:
    # Bypass Model.__init__; our override doesn't use base state
    return TinyModel.__new__(TinyModel)


def run_agent(agent, state):
    return asyncio.run(agent(state))


def make_messages(n_tail: int) -> list[Any]:
    # Build a long message list: [System, User] + n_tail Assistant messages
    from inspect_ai.model._chat_message import ChatMessageAssistant, ChatMessageSystem, ChatMessageUser

    msgs: list[Any] = [ChatMessageSystem(content="sys"), ChatMessageUser(content="start")]  # prefix
    msgs.extend(ChatMessageAssistant(content=f"A{i}") for i in range(n_tail))
    return msgs


def count_assistant(messages: list[Any]) -> int:
    from inspect_ai.model._chat_message import ChatMessageAssistant

    return sum(1 for m in messages if isinstance(m, ChatMessageAssistant))


def test_prune_uses_max_turns_tail(monkeypatch):
    # Arrange: long history beyond tail; max_turns=10 => tail_window=20
    from inspect_ai.agent._agent import AgentState

    msgs = make_messages(100)
    state = AgentState(messages=msgs)

    agent = build_iterative_agent(
        model=dummy_model(),
        max_steps=1,
        max_turns=10,
        max_messages=None,
    )

    # Act
    new_state = run_agent(agent, state)

    # Assert: kept first 2 + last 20, then +2 added during loop (assistant + user continue)
    expected = 2 + 20 + 2
    assert len(new_state.messages) == expected


def test_prune_uses_max_messages_over_max_turns(monkeypatch):
    # Arrange: long history beyond tail; max_messages=60 should override max_turns
    from inspect_ai.agent._agent import AgentState

    msgs = make_messages(100)
    state = AgentState(messages=msgs)

    agent = build_iterative_agent(
        model=dummy_model(),
        max_steps=1,
        max_turns=3,  # would keep 6 if used
        max_messages=60,
    )

    # Act
    new_state = run_agent(agent, state)

    # Assert: kept first 2 + last 60, then +2 added during loop
    expected = 2 + 60 + 2
    assert len(new_state.messages) == expected


def test_env_fallback_max_steps(monkeypatch):
    # Arrange: no explicit max_steps, env sets to 3
    from inspect_ai.agent._agent import AgentState

    monkeypatch.setenv("INSPECT_ITERATIVE_MAX_STEPS", "3")
    # Ensure time limit not interfering
    monkeypatch.delenv("INSPECT_ITERATIVE_TIME_LIMIT", raising=False)

    agent = build_iterative_agent(model=dummy_model(), max_steps=None)
    state = AgentState(messages=[])

    # Act
    new_state = run_agent(agent, state)

    # Assert: assistant messages appended equals 3 steps
    assert count_assistant(new_state.messages) == 3


def test_env_zero_time_limit_normalized(monkeypatch):
    # Arrange: time limit from env is '0' -> should be treated as unset (None)
    from inspect_ai.agent._agent import AgentState

    monkeypatch.setenv("INSPECT_ITERATIVE_TIME_LIMIT", "0")
    monkeypatch.delenv("INSPECT_ITERATIVE_MAX_STEPS", raising=False)

    agent = build_iterative_agent(model=dummy_model(), max_steps=1)
    state = AgentState(messages=[])

    # Act
    new_state = run_agent(agent, state)

    # Assert: completed at least one assistant step (not terminated by time=0)
    assert count_assistant(new_state.messages) == 1


def test_warn_small_max_messages(monkeypatch, caplog):
    # Arrange: small cap triggers a warning
    from inspect_ai.agent._agent import AgentState

    caplog.set_level(logging.WARNING, logger="inspect_agents.iterative")
    agent = build_iterative_agent(model=dummy_model(), max_steps=1, max_messages=4)
    state = AgentState(messages=make_messages(10))

    # Act
    _ = run_agent(agent, state)

    # Assert: a warning mentioning max_messages was emitted
    assert any("max_messages" in rec.getMessage() for rec in caplog.records)

import asyncio
import logging
from typing import Any

from inspect_ai.model._model import Model

from inspect_agents.iterative import build_iterative_agent


class FlakyOncePerCallModel(Model):
    """Model that fails exactly once per generate() call, then succeeds.

    Used to simulate a provider that requires one retry with a controlled
    backoff (handled by our retry wrapper). We rely on a simple toggle to
    alternate failure/success across attempts within a single call, ensuring
    deterministic behavior.
    """

    def __init__(self) -> None:
        self._toggle = False

    async def generate(self, input, tools, config, cache: bool = False):
        from inspect_ai.model._chat_message import ChatMessageAssistant
        from inspect_ai.model._model_output import ModelOutput

        from inspect_agents._model_retry import RetryableGenerateError

        # First attempt in a call fails; second attempt succeeds
        self._toggle = not self._toggle
        if self._toggle:
            raise RetryableGenerateError("retry me")
        return ModelOutput.from_message(
            ChatMessageAssistant(content="ok", source="generate")
        )


def _run(agent, state):
    return asyncio.run(agent(state))


def _count_assistant(messages: list[Any]) -> int:
    from inspect_ai.model._chat_message import ChatMessageAssistant

    return sum(1 for m in messages if isinstance(m, ChatMessageAssistant))


def test_productive_time_increases_steps(monkeypatch):
    """With productive-time enabled, subtracting retry waits allows more steps."""
    from inspect_ai.agent._agent import AgentState

    # Speed up retries for test determinism; zero jitter
    monkeypatch.setenv("INSPECT_RETRY_INITIAL_SECONDS", "0.1")
    monkeypatch.setenv("INSPECT_RETRY_JITTER", "0")
    monkeypatch.setenv("INSPECT_RETRY_MAX_ATTEMPTS", "4")

    # Common agent config: small time budget, ample max_steps
    time_budget = 1  # seconds
    max_steps = 50

    # OFF (wall-clock only): no subtraction
    monkeypatch.delenv("INSPECT_PRODUCTIVE_TIME", raising=False)
    agent_off = build_iterative_agent(model=FlakyOncePerCallModel(), max_steps=max_steps, real_time_limit_sec=time_budget)
    state_off = AgentState(messages=[])
    new_off = _run(agent_off, state_off)
    off_steps = _count_assistant(new_off.messages)

    # ON (productive-time): subtract retry waits
    monkeypatch.setenv("INSPECT_PRODUCTIVE_TIME", "1")
    agent_on = build_iterative_agent(model=FlakyOncePerCallModel(), max_steps=max_steps, real_time_limit_sec=time_budget)
    state_on = AgentState(messages=[])
    new_on = _run(agent_on, state_on)
    on_steps = _count_assistant(new_on.messages)

    # Expect more completed steps when productive-time accounting is enabled
    assert on_steps > off_steps


def test_progress_logs_include_metrics(monkeypatch, caplog):
    """Progress logs report elapsed, retry, and productive times when enabled."""
    from inspect_ai.agent._agent import AgentState

    # Enable productive-time and frequent progress logging
    monkeypatch.setenv("INSPECT_PRODUCTIVE_TIME", "1")
    monkeypatch.setenv("INSPECT_RETRY_INITIAL_SECONDS", "0.1")
    monkeypatch.setenv("INSPECT_RETRY_JITTER", "0")
    caplog.set_level(logging.INFO, logger="inspect_agents.iterative")

    agent = build_iterative_agent(
        model=FlakyOncePerCallModel(),
        max_steps=3,
        real_time_limit_sec=1,
        progress_every=1,
    )
    state = AgentState(messages=[])
    _ = _run(agent, state)

    # Verify at least one info log contains the metrics
    msgs = [rec.getMessage() for rec in caplog.records if rec.levelno == logging.INFO]
    assert any("iterative progress: elapsed=" in m and "retry=" in m and "productive=" in m for m in msgs)


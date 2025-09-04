import asyncio

import pytest
from inspect_ai.agent._agent import AgentState
from inspect_ai.model._chat_message import ChatMessageAssistant, ChatMessageSystem, ChatMessageUser
from inspect_ai.model._model import Model
from inspect_ai.model._model_output import ModelOutput

from inspect_agents.iterative import build_iterative_agent


class FakeTokenizer:
    def encode(self, text: str, disallowed_special=()):  # noqa: ARG002
        return [ord(c) for c in text]

    def decode(self, ids):
        return "".join(chr(i) for i in ids)


class NoToolModel(Model):
    async def generate(self, input, tools, config, cache: bool = False):  # noqa: ARG002
        # Return a small assistant message; we want to exercise the prune path
        return ModelOutput.from_message(
            ChatMessageAssistant(content="ok", source="generate")
        )


def _run(agent, state):
    return asyncio.run(agent(state))


@pytest.mark.truncation
def test_iterative_per_message_truncate_threshold(monkeypatch):
    # Ensure tokenization is available and deterministic even without tiktoken
    import inspect_agents._conversation as conv

    monkeypatch.setattr(conv, "_get_tokenizer", lambda: FakeTokenizer())

    # Build an agent with per-message token cap enabled via param
    agent = build_iterative_agent(
        model=NoToolModel.__new__(NoToolModel),
        max_steps=1,
        max_turns=0,  # disable _prune_history so threshold path triggers
        prune_after_messages=3,
        prune_keep_last=3,
        per_msg_token_cap=50,
        truncate_last_k=2,
    )

    # Seed conversation to exceed threshold: system + two long user/assistant
    msgs = [
        ChatMessageSystem(content="sys"),
        ChatMessageUser(content="U" * 400),
        ChatMessageAssistant(content="A" * 400),
        ChatMessageUser(content="B" * 400),  # last two eligible -> truncated
    ]
    state = AgentState(messages=msgs)

    new_state = _run(agent, state)

    # After one step, verify that at least the last message was truncated
    last_user = next(m for m in reversed(new_state.messages) if isinstance(m, ChatMessageUser))
    assert "tokens trimmed" in (last_user.text or last_user.content or "")


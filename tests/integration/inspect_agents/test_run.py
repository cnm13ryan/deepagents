import asyncio

import pytest
from inspect_ai.agent._agent import AgentState, agent
from inspect_ai.model._chat_message import ChatMessageAssistant, ChatMessageUser
from inspect_ai.tool._tool_call import ToolCall

from inspect_agents.agents import build_supervisor
from inspect_agents.run import run_agent


@agent
def toy_submit_model():
    async def execute(state: AgentState, tools):
        state.messages.append(
            ChatMessageAssistant(
                content="",
                tool_calls=[
                    ToolCall(id="1", function="submit", arguments={"answer": "DONE"})
                ],
            )
        )
        return state

    return execute


def _supervisor():
    return build_supervisor(
        prompt="You are helpful.", tools=[], attempts=1, model=toy_submit_model()
    )


def test_run_with_str_input_returns_state():
    agent_obj = _supervisor()
    result = asyncio.run(run_agent(agent_obj, "start"))

    assert isinstance(result, AgentState)
    assert len(result.messages) >= 2
    assert "DONE" in (result.output.completion or "")


def test_run_with_messages_input_returns_state():
    agent_obj = _supervisor()
    msgs = [ChatMessageUser(content="begin")]
    result = asyncio.run(run_agent(agent_obj, msgs))

    assert isinstance(result, AgentState)
    assert len(result.messages) >= 2
    assert "DONE" in (result.output.completion or "")


def test_run_return_limit_error_tuple_when_limit_exceeded():
    from inspect_ai.util import LimitExceededError, time_limit

    agent_obj = _supervisor()
    # time_limit(0) will elapse by context exit, triggering a LimitExceededError
    result = asyncio.run(
        run_agent(
            agent_obj,
            "start",
            limits=[time_limit(0)],
            return_limit_error=True,
        )
    )

    # Expect a (state, err) tuple with a LimitExceededError instance
    assert isinstance(result, tuple) and len(result) == 2
    state, err = result
    assert isinstance(state, AgentState)
    assert isinstance(err, LimitExceededError)


def test_run_raise_on_limit_raises_exception():
    from inspect_ai.util import LimitExceededError, time_limit

    agent_obj = _supervisor()
    with pytest.raises(LimitExceededError):
        asyncio.run(
            run_agent(
                agent_obj,
                "start",
                limits=[time_limit(0)],
                raise_on_limit=True,
            )
        )

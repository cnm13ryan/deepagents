import asyncio

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


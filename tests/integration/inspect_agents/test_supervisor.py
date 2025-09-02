import asyncio

from inspect_ai.agent._agent import AgentState, agent
from inspect_ai.model._chat_message import ChatMessageAssistant, ChatMessageUser
from inspect_ai.tool._tool_call import ToolCall

from inspect_agents.agents import build_supervisor


@agent
def toy_submit_model():
    async def execute(state: AgentState, tools):
        # Immediately call submit with a final answer
        state.messages.append(
            ChatMessageAssistant(
                content="", tool_calls=[ToolCall(id="1", function="submit", arguments={"answer": "DONE"})]
            )
        )
        return state

    return execute


def test_supervisor_runs_and_submits():
    # Build supervisor with toy model that always submits
    agent = build_supervisor(
        prompt="You are helpful.", tools=[], attempts=1, model=toy_submit_model()
    )

    # Kick off with a user message
    state = AgentState(messages=[ChatMessageUser(content="start")])

    result = asyncio.run(agent(state))

    # Completion should include the submitted answer
    assert "DONE" in (result.output.completion or "")


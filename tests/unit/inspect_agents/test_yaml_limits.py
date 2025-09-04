import asyncio

from inspect_ai.agent._agent import AgentState, agent
from inspect_ai.model._chat_message import ChatMessageAssistant

from inspect_agents.config import load_and_build


@agent
def one_reply_agent():
    async def execute(state: AgentState, tools):
        # Appends one assistant message (will exceed message_limit=1 once added)
        state.messages.append(ChatMessageAssistant(content="hello"))
        return state

    return execute


def test_yaml_message_limit_enforced():
    yaml_txt = """
    supervisor:
      prompt: "You are helpful."
    limits:
      - type: message
        value: 1
    """

    agent_obj, _tools, _approvals, limits = load_and_build(
        yaml_txt, model=one_reply_agent()
    )

    # Use Inspect's agent runner directly to observe limit errors
    from inspect_ai.agent._run import run as agent_run

    state, err = asyncio.run(agent_run(agent_obj, "start", limits=limits))

    # Either the limit error is returned or the run is clipped early
    # (Inspect returns (state, LimitExceededError) when catch_errors=True)
    assert err is not None
    from inspect_ai.util._limit import LimitExceededError

    assert isinstance(err, LimitExceededError)


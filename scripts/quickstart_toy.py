# quickstart_toy.py
import asyncio

from inspect_ai.agent._agent import AgentState, agent
from inspect_ai.model._chat_message import ChatMessageAssistant

from inspect_agents.agents import build_supervisor
from inspect_agents.run import run_agent


@agent
def toy_submit_model():
    async def execute(state: AgentState, tools):
        state.messages.append(
            ChatMessageAssistant(
                content="",
                tool_calls=[{"id": "1", "function": "submit", "arguments": {"answer": "DONE"}}],
            )
        )
        return state
    return execute

async def main():
    sup = build_supervisor(prompt="You are helpful.", tools=[], attempts=1, model=toy_submit_model())
    result = await run_agent(sup, "hello")
    print("Completion:", result.output.completion)

asyncio.run(main())
# Expected output: "Completion: DONE"

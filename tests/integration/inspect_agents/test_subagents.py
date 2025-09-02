import asyncio

from inspect_ai.model._chat_message import (
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageTool,
    ChatMessageUser,
)
from inspect_ai.tool._tool_call import ToolCall
from inspect_ai.model._call_tools import execute_tools
from inspect_ai.agent._agent import AgentState, agent
from inspect_ai.util._store import Store, init_subtask_store, store

from inspect_agents.agents import build_subagents


@agent(description="Sub agent that reads from the Store and replies")
def sub_read_agent():
    async def execute(state: AgentState, tools: list = []):
        val = store().get("shared", None)
        
        # Create assistant message with submit tool call to exit the react loop
        assistant_message = ChatMessageAssistant(
            content=f"shared={val}",
            tool_calls=[ToolCall(id="submit_1", function="submit", arguments={"answer": f"shared={val}"})]
        )
        state.messages.append(assistant_message)
        return state

    return execute


def _conv_with_handoff(function: str):
    return [
        ChatMessageUser(content="top-level start"),
        ChatMessageAssistant(
            content="",
            tool_calls=[ToolCall(id="1", function=function, arguments={})],
        ),
    ]


def test_handoff_boundary_and_prefix_and_ids():
    # Shared store visible to sub-agents
    s = Store(); init_subtask_store(s); s.set("shared", "XYZ")

    tools = build_subagents(
        configs=[
            dict(
                name="reader",
                description="Reads shared store",
                prompt="You read from store",
                model=sub_read_agent(),
            )
        ],
        base_tools=[],
    )
    handoff_tool = tools[0]

    # Build conversation with a transfer tool call
    messages = _conv_with_handoff("transfer_to_reader")
    original_ids = [m.id for m in messages]

    # Execute the handoff
    result = asyncio.run(execute_tools(messages, [handoff_tool]))
    added = result.messages

    # Boundary: first added message is ChatMessageTool with transfer success
    assert isinstance(added[0], ChatMessageTool)
    assert added[0].content == "Successfully transferred to reader."

    # Only new messages appended: none of the new ids were in original ids
    assert all(m.id not in original_ids for m in added)

    # Assistant messages are prefixed with [reader]
    assert any(
        isinstance(m, ChatMessageAssistant) and "[reader]" in (m.text or "")
        for m in added
    )

    # Store value was visible to the sub-agent and included in reply
    assert any(
        isinstance(m, ChatMessageAssistant) and "shared=XYZ" in m.text for m in added
    )

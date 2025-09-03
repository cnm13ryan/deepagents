# test(subagents): verify input/output filtering for handoffs

import os
from typing import List

import pytest


@pytest.mark.asyncio
async def test_subagent_input_and_supervisor_output_filters(monkeypatch):
    """Ensure sub-agent receives filtered history and supervisor gets filtered output.

    - Input filtering: no tool/system messages; bounded context (<= 2 messages) ending
      with the synthetic transfer boundary.
    - Output filtering: supervisor only receives content-only messages (no system
      messages and no tool_calls on assistant messages), with assistant content
      prefixed by the agent name and a trailing user nudge.
    """
    # Force strict quarantine defaults for deterministic behavior
    monkeypatch.setenv("INSPECT_QUARANTINE_MODE", "strict")

    # Imports kept local to avoid heavy module import costs for unrelated tests
    from inspect_ai.agent._agent import AgentState, agent
    from inspect_ai.agent._handoff import handoff
    from inspect_ai.model._call_tools import execute_tools
    from inspect_ai.model._chat_message import (
        ChatMessageAssistant,
        ChatMessageSystem,
        ChatMessageTool,
        ChatMessageUser,
    )
    from inspect_ai.tool import ToolCall
    from inspect_ai.util._store import store

    from inspect_agents.filters import default_input_filter, default_output_filter

    # Spy agent that records the input it sees, then emits an assistant message
    # (with a dummy tool_call) and a system message (which should be dropped from
    # the supervisor-visible output).
    @agent(name="writer", description="spy for filtering")
    def spy_agent():
        async def execute(state: AgentState) -> AgentState:
            s = store()
            # Record observations about the handed-off conversation
            roles = [m.role for m in state.messages]
            has_tool = any(isinstance(m, ChatMessageTool) for m in state.messages)
            has_system = any(isinstance(m, ChatMessageSystem) for m in state.messages)
            s.set("spy:roles", roles)
            s.set("spy:len", len(state.messages))
            s.set("spy:has_tool", has_tool)
            s.set("spy:has_system", has_system)

            # Emit an assistant message that includes a tool_call (to be content-filtered)
            state.messages.append(
                ChatMessageAssistant(
                    content="Spy output",
                    tool_calls=[ToolCall(id="x", function="dummy", arguments={"x": 1})],
                )
            )
            # Emit a system message that should never be surfaced to the supervisor
            state.messages.append(ChatMessageSystem(content="internal-only"))
            return state

        return execute

    # Wrap spy as a handoff tool with default Inspect-Agents filters
    agent_tool = handoff(
        spy_agent(),
        description="Writer sub-agent",
        input_filter=default_input_filter("writer"),
        output_filter=default_output_filter(),
        tool_name="transfer_to_writer",
    )

    # Build a supervisor-side conversation that includes system + tool chatter
    # followed by a handoff call to the writer sub-agent
    messages: List[ChatMessageUser | ChatMessageAssistant | ChatMessageSystem | ChatMessageTool] = [
        ChatMessageSystem(content="supervisor system instructions"),
        ChatMessageUser(content="Please delegate to writer."),
        ChatMessageTool(content="earlier tool output", tool_call_id="prev", function="read_file"),
        ChatMessageAssistant(
            content="delegating",
            tool_calls=[ToolCall(id="call1", function="transfer_to_writer", arguments={})],
        ),
    ]

    # Execute the handoff via tool execution
    result = await execute_tools(messages, [agent_tool])

    # 1) Sub-agent input history is filtered
    s = store()
    roles = s.get("spy:roles")
    assert roles is not None and isinstance(roles, list)
    assert s.get("spy:has_tool") is False, "tools must be removed from sub-agent input"
    assert s.get("spy:has_system") is False, "system messages must be removed from sub-agent input"
    assert s.get("spy:len") <= 2, "input context should be tightly bounded (<= 2 messages)"
    # The last handed-off message should be the boundary text as a user message
    assert roles[-1] == "user"

    # 2) Supervisor history only receives filtered output from sub-agent
    # Result messages consist of the handoff boundary (tool) followed by filtered agent messages
    assert len(result.messages) >= 2
    assert isinstance(result.messages[0], ChatMessageTool)
    assert result.messages[0].content == "Successfully transferred to writer."

    # All subsequent messages must be content-only (no system; assistant has no tool_calls)
    agent_msgs = result.messages[1:]
    assert all(not isinstance(m, ChatMessageSystem) for m in agent_msgs)
    assistant_msgs = [m for m in agent_msgs if isinstance(m, ChatMessageAssistant)]
    assert len(assistant_msgs) >= 1
    assert all(getattr(m, "tool_calls", None) is None for m in assistant_msgs)
    # Assistant content should be prefixed with the agent name
    assert assistant_msgs[0].text.startswith("[writer] ")
    # Final message should be a user nudge indicating completion
    assert isinstance(agent_msgs[-1], ChatMessageUser)
    assert agent_msgs[-1].text == "The writer agent has completed its work."


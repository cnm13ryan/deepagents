#!/usr/bin/env python3
"""Integration: execute_tools + handoff exclusivity end-to-end.

Asserts:
- Exactly one successful handoff ChatMessageTool is appended.
- No other successful ChatMessageTool messages are added to the conversation.
- Transcript includes N standardized "skipped" ToolEvents (one per non-selected call).

Notes:
- Uses vendored Inspect-AI modules to ensure consistent policy behavior.
- Keeps error ChatMessageTool messages (from rejected calls) out of the success count.
"""

import asyncio
import sys


def _ensure_vendor_on_path():
    vendor_src = "external/inspect_ai/src"
    if vendor_src not in sys.path:
        sys.path.insert(0, vendor_src)


def test_handoff_exclusive_one_handoff_N_skipped(monkeypatch):
    _ensure_vendor_on_path()

    # Import Inspect-AI building blocks from vendored source
    from inspect_ai.agent._agent import AgentState, agent
    from inspect_ai.agent._handoff import handoff
    from inspect_ai.model._call_tools import execute_tools
    from inspect_ai.model._chat_message import (
        ChatMessageAssistant,
        ChatMessageTool,
        ChatMessageUser,
    )
    from inspect_ai.tool._tool import Tool
    from inspect_ai.tool._tool_def import ToolDef
    from inspect_ai.tool._tool_params import ToolParams
    from inspect_ai.tool._tool_call import ToolCall
    from inspect_ai.log._transcript import ToolEvent, Transcript, init_transcript, transcript

    # Activate only the exclusivity policy to ensure it is applied first
    from inspect_ai.approval._apply import init_tool_approval
    from inspect_agents.approval import handoff_exclusive_policy

    init_tool_approval(handoff_exclusive_policy())

    # Fresh transcript for deterministic assertions
    init_transcript(Transcript())

    # Define a trivial sub-agent and wrap as a handoff tool
    @agent(name="reader", description="returns immediately")
    def reader_agent():  # pragma: no cover - trivial async wrapper
        async def run(state: AgentState) -> AgentState:
            # Emit one assistant and one user message to simulate activity
            state.messages.append(ChatMessageAssistant(content="Reader ok"))
            state.messages.append(ChatMessageUser(content="The reader agent has completed its work."))
            return state

        return run

    handoff_tool = handoff(reader_agent(), description="Reader sub-agent", tool_name="transfer_to_reader")

    # Define two normal tools that would otherwise execute in parallel
    def _echo_tool(name: str, text: str) -> Tool:
        async def execute() -> str:
            return text

        params = ToolParams()  # no-arg tool
        return ToolDef(execute, name=name, description=f"Echo {text}", parameters=params).as_tool()

    echo_a = _echo_tool("echo_a", "A")
    echo_b = _echo_tool("echo_b", "B")

    # Assistant proposes one handoff and 2 normal tools (N=2)
    messages = [
        ChatMessageUser(content="start"),
        ChatMessageAssistant(
            content="",
            tool_calls=[
                ToolCall(id="1", function="transfer_to_reader", arguments={}),
                ToolCall(id="2", function="echo_a", arguments={}),
                ToolCall(id="3", function="echo_b", arguments={}),
            ],
        ),
    ]

    # Execute with all tools available
    result = asyncio.run(execute_tools(messages, [handoff_tool, echo_a, echo_b]))

    # 1) Exactly one successful handoff result message
    tool_msgs = [m for m in result.messages if isinstance(m, ChatMessageTool)]
    handoff_success = [m for m in tool_msgs if m.function.startswith("transfer_to_") and getattr(m, "error", None) is None]
    assert len(handoff_success) == 1

    # 2) No other successful ChatMessageTool messages (skip errors)
    extra_success = [m for m in tool_msgs if not m.function.startswith("transfer_to_") and getattr(m, "error", None) is None]
    assert len(extra_success) == 0

    # 3) Transcript should contain N standardized "skipped" ToolEvents emitted by policy
    events = transcript().events
    skipped = [
        e
        for e in events
        if isinstance(e, ToolEvent)
        and getattr(e, "error", None) is not None
        and getattr(e, "metadata", None) is not None
        and e.metadata.get("source") == "policy/handoff_exclusive"
        and e.metadata.get("selected_handoff_id") == "1"
        and e.metadata.get("skipped_function") in {"echo_a", "echo_b"}
    ]
    assert len(skipped) == 2

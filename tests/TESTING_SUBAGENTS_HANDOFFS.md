# Testing Guide — Subagents & Handoffs

Focus: input/output filtering, boundaries, and content shaping for subagents.

## What to verify
- Input filtering: subagent input excludes tool/system messages and is tightly bounded.
- Output filtering: supervisor receives content-only assistant messages (no tool_calls/system).
- Boundary message: first appended message is a `ChatMessageTool` describing the transfer.
- Prefixing: assistant text is prefixed with `[<agent>]`.
- Completion nudge: trailing user message indicates the subagent finished.

## Patterns
- Build handoff tool via `handoff(agent, description=..., input_filter=..., output_filter=..., tool_name=...)`.
- Use default filters from `inspect_agents.filters` unless a test needs explicit scope.
- Use `store()` to record observations from the subagent for assertions in the supervisor context.

## Tips
- Keep offline and fast; avoid real models by using trivial @agent bodies that synthesize messages.
- Scope any env overrides (`INSPECT_QUARANTINE_MODE`, etc.) with `monkeypatch` per test.

## Examples
- Minimal handoff with default filters and boundary assertions:
  ```python
  import asyncio
  from inspect_ai.agent._agent import AgentState, agent
  from inspect_ai.agent._handoff import handoff
  from inspect_ai.model._call_tools import execute_tools
  from inspect_ai.model._chat_message import ChatMessageAssistant, ChatMessageTool, ChatMessageUser
  from inspect_ai.tool._tool_call import ToolCall
  from inspect_agents.filters import default_input_filter, default_output_filter

  @agent(name="writer")
  def sub():
      async def run(state: AgentState):
          state.messages.append(ChatMessageUser(content="The writer agent has completed its work."))
          return state
      return run

  def test_handoff_boundary():
      tool = handoff(
          sub(),
          description="writer",
          input_filter=default_input_filter("writer"),
          output_filter=default_output_filter(),
          tool_name="transfer_to_writer",
      )
      msg = ChatMessageAssistant(content="", tool_calls=[ToolCall(id="1", function="transfer_to_writer", arguments={})])
      out = asyncio.run(execute_tools([msg], [tool]))
      assert isinstance(out.messages[0], ChatMessageTool)
      assert isinstance(out.messages[-1], ChatMessageUser)
  ```

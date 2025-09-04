# Testing Guide — Limits & Truncation

Covers tool-output truncation envelopes and byte limits.

## What to verify
- Envelope presence and wording when tool output exceeds limit.
- `<START_TOOL_OUTPUT>`/`<END_TOOL_OUTPUT>` markers wrap the truncated payload.
- Bytes inside the envelope equal the configured limit.

## Patterns
- Create a trivial tool returning a large string, call with `max_output=<bytes>`, and assert envelope + payload length.
- Keep assertions byte-precise by measuring `len(payload.encode('utf-8'))`.

## Examples
- Minimal truncation assertion:
  ```python
  import asyncio
  from inspect_ai.model._call_tools import execute_tools
  from inspect_ai.model._chat_message import ChatMessageAssistant, ChatMessageTool, ChatMessageUser
  from inspect_ai.tool._tool_def import ToolDef
  from inspect_ai.tool._tool_params import ToolParams

  def long_output_tool():
      async def execute() -> str:
          return "x" * 500
      return ToolDef(execute, name="long_output", description="", parameters=ToolParams()).as_tool()

  def test_truncation_envelope():
      tool = long_output_tool()
      msgs = [ChatMessageUser(content="go"), ChatMessageAssistant(content="", tool_calls=[dict(id="1", function="long_output", arguments={})])]
      result = asyncio.run(execute_tools(msgs, [tool], max_output=100))
      tm = next(m for m in result.messages if isinstance(m, ChatMessageTool))
      text = tm.content if isinstance(tm.content, str) else "".join(getattr(c, "text", "") for c in tm.content)
      assert "<START_TOOL_OUTPUT>" in text and "<END_TOOL_OUTPUT>" in text
  ```

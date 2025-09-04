import asyncio

from inspect_ai.model._chat_message import ChatMessageAssistant, ChatMessageUser
from inspect_ai.tool._tool import Tool, tool
from inspect_ai.util._store import Store, init_subtask_store
from inspect_ai.util._store_model import store_as

from inspect_agents.migration import _apply_side_effect_calls
from inspect_agents.state import Files, Todos


@tool()
def mark_store() -> Tool:  # type: ignore[return-type]
    async def execute(path: str, content: str) -> str:
        """Write content to a store-backed file.

        Args:
            path: Destination path key.
            content: Text to store.
        """
        files = store_as(Files)
        files.put_file(path, content)
        return "OK"

    return execute


def test_apply_side_effect_calls_executes_tools_path():
    # Isolate store per test
    s = Store()
    init_subtask_store(s)

    # Synthetic conversation where assistant proposes a non-submit + submit
    messages = [
        ChatMessageUser(content="start"),
        ChatMessageAssistant(
            content="",
            tool_calls=[
                {"id": "1", "function": "mark_store", "arguments": {"path": "m.txt", "content": "marker"}},
                {"id": "2", "function": "submit", "arguments": {"answer": "OK"}},
            ],
        ),
    ]

    async def run():
        await _apply_side_effect_calls(messages, [mark_store()])

    asyncio.run(run())

    # Execute-tools path should have written via custom tool (not covered by fallback)
    files = store_as(Files)
    assert files.get_file("m.txt") == "marker"


def test_apply_side_effect_calls_fallback_path():
    # Isolate store per test
    s = Store()
    init_subtask_store(s)

    # Assistant proposes built-in side-effect tools, plus submit
    messages = [
        ChatMessageUser(content="start"),
        ChatMessageAssistant(
            content="",
            tool_calls=[
                {
                    "id": "1",
                    "function": "write_todos",
                    "arguments": {"todos": [{"content": "do x", "status": "pending"}]},
                },
                {
                    "id": "2",
                    "function": "write_file",
                    "arguments": {"file_path": "a.txt", "content": "hello"},
                },
                {"id": "3", "function": "submit", "arguments": {"answer": "OK"}},
            ],
        ),
    ]

    async def run():
        # No tools passed -> execute_tools path is unavailable; fallback should apply
        await _apply_side_effect_calls(messages, [])

    asyncio.run(run())

    # Verify fallback applied state updates
    files = store_as(Files)
    assert files.get_file("a.txt") == "hello"
    todos = store_as(Todos).get_todos()
    assert any(t.content == "do x" for t in todos)

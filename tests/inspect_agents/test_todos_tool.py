import asyncio

from inspect_ai.util._store import Store, init_subtask_store

from inspect_agents.state import Todo, Todos
from inspect_agents.tools import write_todos


def _fresh_store() -> Store:
    s = Store()
    init_subtask_store(s)
    return s


def test_write_todos_updates_store_and_returns_message():
    s = _fresh_store()
    tool = write_todos()

    todos = [Todo(content="one", status="pending"), Todo(content="two", status="completed")]

    async def _run():
        return await tool(todos=todos)

    result = asyncio.run(_run())

    # Output mirrors legacy human-readable confirmation
    expected = f"Updated todo list to {[t.model_dump() for t in todos]}"
    assert result == expected

    # Store updates reflected via StoreModel
    model = Todos(store=s)
    assert [t.model_dump() for t in model.get_todos()] == [t.model_dump() for t in todos]


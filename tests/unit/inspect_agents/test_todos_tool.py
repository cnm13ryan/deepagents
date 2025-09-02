import asyncio
import pytest

from inspect_ai.util._store import Store, init_subtask_store

from inspect_agents.state import Todo, Todos
from inspect_agents.tools import write_todos, update_todo_status, ToolException


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


def test_update_todo_status_error_handling():
    _fresh_store()
    write_tool = write_todos()
    update_tool = update_todo_status()

    # First create a todo list
    todos = [Todo(content="task1", status="pending"), Todo(content="task2", status="pending")]
    
    async def _setup():
        return await write_tool(todos=todos)
    
    asyncio.run(_setup())
    
    # Test invalid index (too high)
    async def _invalid_index_high():
        await update_tool(todo_index=10, status="in_progress")
    
    with pytest.raises(ToolException) as exc_info:
        asyncio.run(_invalid_index_high())
    assert "Invalid todo operation" in str(exc_info.value.message)
    
    # Test invalid index (negative)
    async def _invalid_index_negative():
        await update_tool(todo_index=-1, status="in_progress")
    
    with pytest.raises(ToolException) as exc_info:
        asyncio.run(_invalid_index_negative())
    assert "Invalid todo operation" in str(exc_info.value.message)
    
    # Test invalid status
    async def _invalid_status():
        await update_tool(todo_index=0, status="invalid_status")
    
    with pytest.raises(ToolException) as exc_info:
        asyncio.run(_invalid_status())
    assert "Invalid todo operation" in str(exc_info.value.message)
    assert "Invalid status" in str(exc_info.value.message)

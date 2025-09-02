import asyncio
import pytest

from inspect_ai.util._store import Store, init_subtask_store
from inspect_ai.util._span import span
from inspect_ai.log._transcript import Transcript, init_transcript, transcript, StoreEvent

from inspect_agents.state import Todo, Todos, Files


def _fresh_store_and_transcript() -> Store:
    s = Store()
    init_subtask_store(s)
    init_transcript(Transcript())
    return s


def test_todos_default_and_set_get():
    s = _fresh_store_and_transcript()

    todos = Todos(store=s)
    assert todos.get_todos() == []

    todos.set_todos([Todo(content="x", status="pending")])
    # rebind to confirm persistence through Store
    todos2 = Todos(store=s)
    assert len(todos2.get_todos()) == 1
    assert todos2.get_todos()[0].content == "x"
    assert todos2.get_todos()[0].status == "pending"


def test_files_accessors_and_isolation():
    s = _fresh_store_and_transcript()

    files_shared = Files(store=s)
    files_shared.put_file("a.txt", "hello")
    assert files_shared.get_file("a.txt") == "hello"
    assert "a.txt" in files_shared.list_files()

    # Instance isolation: different instances must not see each other's files
    files_a = Files(store=s, instance="agentA")
    files_b = Files(store=s, instance="agentB")
    files_a.put_file("b.txt", "A-only")
    assert files_a.get_file("b.txt") == "A-only"
    assert files_b.get_file("b.txt") is None


def test_files_delete():
    s = _fresh_store_and_transcript()
    files = Files(store=s)
    files.put_file("to_remove.md", "bye")
    assert "to_remove.md" in files.list_files()

    files.delete_file("to_remove.md")
    assert files.get_file("to_remove.md") is None
    assert "to_remove.md" not in files.list_files()


def test_store_event_recorded_on_change():
    async def _run():
        s = _fresh_store_and_transcript()
        files = Files(store=s)
        async with span("write-file"):
            files.put_file("event.txt", "ok")

    asyncio.run(_run())

    # At least one StoreEvent should be present
    evs = transcript().events
    assert any(isinstance(e, StoreEvent) for e in evs)

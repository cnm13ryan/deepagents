import asyncio
import os
import pytest
from unittest.mock import patch

from inspect_ai.util._store import Store, init_subtask_store

from inspect_agents.tools import (
    ls, read_file, write_file, edit_file, write_todos, update_todo_status,
    FileReadResult, FileWriteResult, FileEditResult, FileListResult,
    TodoWriteResult, TodoStatusResult
)
from inspect_agents.state import Todo, Files


def _fresh_store() -> Store:
    s = Store()
    init_subtask_store(s)
    return s


@pytest.fixture(autouse=True)
def clean_env():
    """Ensure clean environment for each test."""
    old_env = os.environ.get("INSPECT_AGENTS_TYPED_RESULTS")
    yield
    if old_env is not None:
        os.environ["INSPECT_AGENTS_TYPED_RESULTS"] = old_env
    else:
        os.environ.pop("INSPECT_AGENTS_TYPED_RESULTS", None)


class TestTypedResults:
    """Test typed results functionality behind environment flag."""
    
    def test_ls_typed_result(self):
        """Test ls tool returns FileListResult when flag is set."""
        s = _fresh_store()
        ls_tool = ls()
        write_tool = write_file()

        # Setup some files
        async def _setup():
            await write_tool(file_path="a.txt", content="hello")
            await write_tool(file_path="b.txt", content="world")

        asyncio.run(_setup())

        with patch.dict(os.environ, {"INSPECT_AGENTS_TYPED_RESULTS": "1"}):
            async def _test_typed():
                return await ls_tool()
            
            result = asyncio.run(_test_typed())
            assert isinstance(result, FileListResult)
            assert "a.txt" in result.files
            assert "b.txt" in result.files

        # Without flag, should return list
        async def _test_legacy():
            return await ls_tool()
        
        result = asyncio.run(_test_legacy())
        assert isinstance(result, list)
        assert "a.txt" in result
        assert "b.txt" in result

    def test_read_file_typed_result(self):
        """Test read_file tool returns FileReadResult when flag is set."""
        s = _fresh_store()
        read_tool = read_file()
        write_tool = write_file()

        # Setup a file
        test_content = "line1\nline2\nline3"
        async def _setup():
            await write_tool(file_path="test.txt", content=test_content)

        asyncio.run(_setup())

        with patch.dict(os.environ, {"INSPECT_AGENTS_TYPED_RESULTS": "1"}):
            async def _test_typed():
                return await read_tool(file_path="test.txt")
            
            result = asyncio.run(_test_typed())
            assert isinstance(result, FileReadResult)
            assert len(result.lines) == 3
            assert "test.txt" in result.summary
            # Check formatted lines
            assert "1\tline1" in result.lines[0]
            assert "2\tline2" in result.lines[1]
            assert "3\tline3" in result.lines[2]

        # Without flag, should return formatted string
        async def _test_legacy():
            return await read_tool(file_path="test.txt")
        
        result = asyncio.run(_test_legacy())
        assert isinstance(result, str)
        assert "1\tline1" in result
        assert "2\tline2" in result
        assert "3\tline3" in result

    def test_read_file_empty_typed_result(self):
        """Test read_file with empty file returns proper typed result."""
        s = _fresh_store()
        read_tool = read_file()
        write_tool = write_file()

        async def _setup():
            await write_tool(file_path="empty.txt", content="")

        asyncio.run(_setup())

        with patch.dict(os.environ, {"INSPECT_AGENTS_TYPED_RESULTS": "1"}):
            async def _test_typed():
                return await read_tool(file_path="empty.txt")
            
            result = asyncio.run(_test_typed())
            assert isinstance(result, FileReadResult)
            assert result.lines == []
            assert "empty contents" in result.summary

    def test_write_file_typed_result(self):
        """Test write_file tool returns FileWriteResult when flag is set."""
        s = _fresh_store()
        write_tool = write_file()

        with patch.dict(os.environ, {"INSPECT_AGENTS_TYPED_RESULTS": "1"}):
            async def _test_typed():
                return await write_tool(file_path="new.txt", content="hello world")
            
            result = asyncio.run(_test_typed())
            assert isinstance(result, FileWriteResult)
            assert result.path == "new.txt"
            assert "Updated file new.txt" in result.summary

        # Without flag, should return string
        async def _test_legacy():
            return await write_tool(file_path="legacy.txt", content="hello")
        
        result = asyncio.run(_test_legacy())
        assert isinstance(result, str)
        assert "Updated file legacy.txt" in result

    def test_edit_file_typed_result(self):
        """Test edit_file tool returns FileEditResult when flag is set."""
        s = _fresh_store()
        write_tool = write_file()
        edit_tool = edit_file()

        # Setup a file
        async def _setup():
            await write_tool(file_path="edit.txt", content="hello world hello")

        asyncio.run(_setup())

        with patch.dict(os.environ, {"INSPECT_AGENTS_TYPED_RESULTS": "1"}):
            async def _test_typed():
                return await edit_tool(
                    file_path="edit.txt",
                    old_string="hello",
                    new_string="hi",
                    replace_all=False
                )
            
            result = asyncio.run(_test_typed())
            assert isinstance(result, FileEditResult)
            assert result.path == "edit.txt"
            assert result.replaced == 1
            assert "Updated file edit.txt" in result.summary

        # Test replace_all
        with patch.dict(os.environ, {"INSPECT_AGENTS_TYPED_RESULTS": "1"}):
            async def _test_typed_all():
                await write_tool(file_path="edit2.txt", content="hello world hello")
                return await edit_tool(
                    file_path="edit2.txt",
                    old_string="hello",
                    new_string="hi",
                    replace_all=True
                )
            
            result = asyncio.run(_test_typed_all())
            assert isinstance(result, FileEditResult)
            assert result.replaced == 2

    def test_write_todos_typed_result(self):
        """Test write_todos tool returns TodoWriteResult when flag is set."""
        s = _fresh_store()
        write_tool = write_todos()

        todos = [
            Todo(content="task1", status="pending"),
            Todo(content="task2", status="completed")
        ]

        with patch.dict(os.environ, {"INSPECT_AGENTS_TYPED_RESULTS": "1"}):
            async def _test_typed():
                return await write_tool(todos=todos)
            
            result = asyncio.run(_test_typed())
            assert isinstance(result, TodoWriteResult)
            assert result.count == 2
            assert "Updated todo list" in result.summary

        # Without flag, should return string
        async def _test_legacy():
            return await write_tool(todos=todos)
        
        result = asyncio.run(_test_legacy())
        assert isinstance(result, str)
        assert "Updated todo list" in result

    def test_update_todo_status_typed_result(self):
        """Test update_todo_status tool returns TodoStatusResult when flag is set."""
        s = _fresh_store()
        write_tool = write_todos()
        update_tool = update_todo_status()

        todos = [Todo(content="task1", status="pending")]
        
        async def _setup():
            await write_tool(todos=todos)

        asyncio.run(_setup())

        with patch.dict(os.environ, {"INSPECT_AGENTS_TYPED_RESULTS": "1"}):
            async def _test_typed():
                return await update_tool(
                    todo_index=0,
                    status="completed",
                    allow_direct_complete=True
                )
            
            result = asyncio.run(_test_typed())
            assert isinstance(result, TodoStatusResult)
            assert result.index == 0
            assert result.status == "completed"
            assert result.warning is not None  # Direct completion warning
            assert "Updated todo[0] status to completed" in result.summary

        # Without flag, should return JSON string
        todos2 = [Todo(content="task2", status="pending")]
        async def _setup2():
            await write_tool(todos=todos2)

        asyncio.run(_setup2())
        
        async def _test_legacy():
            return await update_tool(todo_index=0, status="in_progress")
        
        result = asyncio.run(_test_legacy())
        assert isinstance(result, str)
        import json
        parsed = json.loads(result)
        assert parsed["ok"] is True
        assert "Updated todo[0] status to in_progress" in parsed["message"]

    def test_environment_flag_variations(self):
        """Test different environment flag values."""
        s = _fresh_store()
        ls_tool = ls()
        write_tool = write_file()

        async def _setup():
            await write_tool(file_path="test.txt", content="hello")

        asyncio.run(_setup())

        # Test truthy values
        for val in ["1", "true", "TRUE", "yes", "YES", "on", "ON"]:
            with patch.dict(os.environ, {"INSPECT_AGENTS_TYPED_RESULTS": val}):
                async def _test():
                    return await ls_tool()
                
                result = asyncio.run(_test())
                assert isinstance(result, FileListResult), f"Failed for value: {val}"

        # Test falsy values
        for val in ["0", "false", "FALSE", "no", "NO", "off", "OFF", ""]:
            with patch.dict(os.environ, {"INSPECT_AGENTS_TYPED_RESULTS": val}):
                async def _test():
                    return await ls_tool()
                
                result = asyncio.run(_test())
                assert isinstance(result, list), f"Failed for value: {val}"

        # Test unset
        if "INSPECT_AGENTS_TYPED_RESULTS" in os.environ:
            del os.environ["INSPECT_AGENTS_TYPED_RESULTS"]
        
        async def _test_unset():
            return await ls_tool()
        
        result = asyncio.run(_test_unset())
        assert isinstance(result, list)
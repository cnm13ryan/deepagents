"""Tests for Pydantic input validation with extra="forbid"."""

from unittest.mock import Mock, patch

import pytest

from inspect_agents.tool_types import (
    FilesToolParams,
    TodoItem,
    UpdateTodoStatusParams,
    WriteTodosParams,
)
from inspect_agents.tools import update_todo_status, write_todos
from inspect_agents.tools_files import FilesParams, LsParams, files_tool


class TestPydanticValidation:
    """Test suite for Pydantic validation with extra='forbid'."""

    def test_files_tool_params_extra_forbid(self):
        """Test that FilesToolParams rejects unknown fields."""
        # Valid params should work
        valid_params = FilesToolParams(command="read", file_path="test.txt", offset=0, limit=100)
        assert valid_params.command == "read"
        assert valid_params.file_path == "test.txt"

        # Unknown field should be rejected
        with pytest.raises(Exception) as exc_info:
            FilesToolParams(command="read", file_path="test.txt", unknown_field="should_fail")
        assert "extra fields not permitted" in str(exc_info.value) or "Extra inputs are not permitted" in str(
            exc_info.value
        )

    def test_todo_item_extra_forbid(self):
        """Test that TodoItem rejects unknown fields."""
        # Valid todo should work
        valid_todo = TodoItem(content="Test task", status="pending")
        assert valid_todo.content == "Test task"
        assert valid_todo.status == "pending"

        # Unknown field should be rejected
        with pytest.raises(Exception) as exc_info:
            TodoItem(content="Test task", status="pending", extra_field="not_allowed")
        assert "extra fields not permitted" in str(exc_info.value) or "Extra inputs are not permitted" in str(
            exc_info.value
        )

    def test_write_todos_params_extra_forbid(self):
        """Test that WriteTodosParams rejects unknown fields."""
        # Valid params should work
        todos = [TodoItem(content="Task 1"), TodoItem(content="Task 2")]
        valid_params = WriteTodosParams(todos=todos)
        assert len(valid_params.todos) == 2

        # Unknown field should be rejected
        with pytest.raises(Exception) as exc_info:
            WriteTodosParams(todos=todos, extra_field="should_fail")
        assert "extra fields not permitted" in str(exc_info.value) or "Extra inputs are not permitted" in str(
            exc_info.value
        )

    def test_update_todo_status_params_extra_forbid(self):
        """Test that UpdateTodoStatusParams rejects unknown fields."""
        # Valid params should work
        valid_params = UpdateTodoStatusParams(todo_index=0, status="completed", allow_direct_complete=True)
        assert valid_params.todo_index == 0
        assert valid_params.status == "completed"

        # Unknown field should be rejected
        with pytest.raises(Exception) as exc_info:
            UpdateTodoStatusParams(todo_index=0, status="completed", invalid_field="not_allowed")
        assert "extra fields not permitted" in str(exc_info.value) or "Extra inputs are not permitted" in str(
            exc_info.value
        )

    def test_files_tool_params_literal_validation(self):
        """Test that FilesToolParams enforces literal command values."""
        # Valid command should work
        valid_params = FilesToolParams(command="ls")
        assert valid_params.command == "ls"

        # Invalid command should be rejected
        with pytest.raises(Exception) as exc_info:
            FilesToolParams(command="invalid_command")
        assert "Input should be" in str(exc_info.value)

    def test_todo_status_literal_validation(self):
        """Test that todo status is validated against literal values."""
        # Valid status should work
        valid_params = UpdateTodoStatusParams(todo_index=0, status="in_progress")
        assert valid_params.status == "in_progress"

        # Invalid status should be rejected
        with pytest.raises(Exception) as exc_info:
            UpdateTodoStatusParams(todo_index=0, status="invalid_status")
        assert "Input should be" in str(exc_info.value)


class TestFilesToolValidationIntegration:
    """Integration tests for files tool validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tool = files_tool()

    @pytest.mark.asyncio
    async def test_files_tool_with_valid_params(self):
        """Test files tool works with valid parameters."""
        with (
            patch("inspect_agents.tools_files._use_sandbox_fs", return_value=False),
            patch("inspect_agents.tools_files._use_typed_results", return_value=False),
            patch("inspect_ai.util._store_model.store_as") as mock_store_as,
        ):
            mock_files = Mock()
            mock_files.list_files.return_value = ["test.txt"]
            mock_store_as.return_value = mock_files

            params = FilesParams(root=LsParams(command="ls"))
            result = await self.tool(params)

            assert result == ["test.txt"]

    @pytest.mark.asyncio
    async def test_files_tool_validation_layer_catches_unknown_fields(self):
        """Test that the validation layer in files_tool catches unknown fields."""
        with (
            patch("inspect_agents.tools_files._use_sandbox_fs", return_value=False),
            patch("inspect_agents.tools_files._use_typed_results", return_value=False),
        ):
            # Create a mock FilesParams that bypasses pydantic validation but contains unknown fields
            mock_params = Mock()
            mock_params.root = Mock()
            mock_params.root.model_dump.return_value = {
                "command": "ls",
                "unknown_field": "should_fail",  # This should trigger our validation
            }

            with pytest.raises(Exception) as exc_info:
                await self.tool(mock_params)

            assert "Invalid parameters" in str(exc_info.value)


class TestTodoToolValidationIntegration:
    """Integration tests for todo tool validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.write_tool = write_todos()
        self.update_tool = update_todo_status()

    @pytest.mark.asyncio
    async def test_write_todos_validation_integration(self):
        """Test that write_todos validation layer works."""
        from inspect_agents.state import Todo

        # Test that validation passes for valid todos
        todos = [Todo(content="Test task", status="pending")]

        # Mock the validation path - we just want to ensure validation doesn't raise
        with (
            patch("inspect_ai.util._store_model.store_as") as mock_store_as,
            patch("inspect_agents.tools._use_typed_results", return_value=False),
        ):
            mock_todos = Mock()
            mock_todos.todos = []
            mock_todos.set_todos = Mock()
            mock_store_as.return_value = mock_todos

            # This should not raise validation errors
            result = await self.write_tool(todos)
            assert "Updated todo list" in result

    @pytest.mark.asyncio
    async def test_update_todo_status_validation_with_invalid_params(self):
        """Test update_todo_status validation catches invalid parameters."""

        # Test that invalid status values are caught by validation layer
        with pytest.raises(Exception) as exc_info:
            await self.update_tool(
                todo_index=0,
                status="invalid_status",  # This should be caught by validation
                allow_direct_complete=False,
            )

        # Should be caught by our Pydantic validation layer
        assert "Invalid todo status parameters" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_write_todos_validation_with_unknown_fields_direct(self):
        """Test that validation catches unknown fields in todos."""

        # This test would be complex to set up with the tool directly, so we test
        # the validation logic more directly by simulating invalid input
        # that bypasses the normal Pydantic parsing but hits our validation layer

        # Create a mock object that would fail validation
        class InvalidTodo:
            def __init__(self):
                self.content = "test"
                self.status = "pending"
                self.invalid_field = "should_fail"  # This would cause validation to fail

            def model_dump(self):
                return {"content": self.content, "status": self.status, "invalid_field": self.invalid_field}

        with (
            patch("inspect_ai.util._store_model.store_as") as mock_store_as,
            patch("inspect_agents.tools._use_typed_results", return_value=False),
        ):
            mock_store_as.return_value = Mock()

            # This should raise our validation error
            with pytest.raises(Exception) as exc_info:
                await self.write_tool([InvalidTodo()])

            assert "Invalid todo parameters" in str(exc_info.value)

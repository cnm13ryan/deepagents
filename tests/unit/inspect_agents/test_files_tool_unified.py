"""Tests for unified files tool with discriminated union."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from inspect_agents.tools_files import (
    EditParams,
    FileEditResult,
    FileListResult,
    FileReadResult,
    FilesParams,
    FileWriteResult,
    LsParams,
    ReadParams,
    WriteParams,
    files_tool,
)


class TestFilesToolUnified:
    """Test suite for the unified files tool."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tool = files_tool()
        
    def test_ls_command_store_mode(self):
        """Test ls command in store mode."""
        async def _test():
            with patch('inspect_agents.tools_files._use_sandbox_fs', return_value=False), \
                 patch('inspect_agents.tools_files._use_typed_results', return_value=False), \
                 patch('inspect_ai.util._store_model.store_as') as mock_store_as:
                
                # Mock Files store
                mock_files = Mock()
                mock_files.list_files.return_value = ['file1.txt', 'file2.txt']
                mock_store_as.return_value = mock_files
                
                params = FilesParams(root=LsParams(command="ls", instance=None))
                result = await self.tool(params)
                
                assert result == ['file1.txt', 'file2.txt']
                mock_store_as.assert_called_once()
                mock_files.list_files.assert_called_once()
        
        asyncio.run(_test())

    @pytest.mark.asyncio
    async def test_ls_command_typed_results(self):
        """Test ls command with typed results."""
        with patch('inspect_agents.tools_files._use_sandbox_fs', return_value=False), \
             patch('inspect_agents.tools_files._use_typed_results', return_value=True), \
             patch('inspect_ai.util._store_model.store_as') as mock_store_as:
            
            mock_files = Mock()
            mock_files.list_files.return_value = ['file1.txt', 'file2.txt']
            mock_store_as.return_value = mock_files
            
            params = FilesParams(root=LsParams(command="ls", instance="test"))
            result = await self.tool(params)
            
            assert isinstance(result, FileListResult)
            assert result.files == ['file1.txt', 'file2.txt']
            mock_store_as.assert_called_with(mock_store_as.call_args[0][0], instance="test")

    @pytest.mark.asyncio
    async def test_read_command_store_mode(self):
        """Test read command in store mode."""
        with patch('inspect_agents.tools_files._use_sandbox_fs', return_value=False), \
             patch('inspect_agents.tools_files._use_typed_results', return_value=False), \
             patch('inspect_agents.tools_files.anyio.fail_after'), \
             patch('inspect_ai.util._store_model.store_as') as mock_store_as:
            
            mock_files = Mock()
            mock_files.get_file.return_value = "line 1\nline 2\nline 3"
            mock_store_as.return_value = mock_files
            
            params = FilesParams(root=ReadParams(
                command="read",
                file_path="test.txt",
                offset=0,
                limit=2,
                instance=None
            ))
            result = await self.tool(params)
            
            # Should format with line numbers
            lines = result.split('\n')
            assert "     1\tline 1" in lines[0]
            assert "     2\tline 2" in lines[1]
            assert len(lines) == 2
            mock_files.get_file.assert_called_once_with("test.txt")

    @pytest.mark.asyncio
    async def test_read_command_file_not_found(self):
        """Test read command when file doesn't exist."""
        with patch('inspect_agents.tools_files._use_sandbox_fs', return_value=False), \
             patch('inspect_agents.tools_files.anyio.fail_after'), \
             patch('inspect_ai.util._store_model.store_as') as mock_store_as:
            
            mock_files = Mock()
            mock_files.get_file.return_value = None
            mock_store_as.return_value = mock_files
            
            params = FilesParams(root=ReadParams(
                command="read",
                file_path="nonexistent.txt"
            ))
            
            with pytest.raises(Exception) as exc_info:
                await self.tool(params)
            assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_read_command_empty_file(self):
        """Test read command with empty file."""
        with patch('inspect_agents.tools_files._use_sandbox_fs', return_value=False), \
             patch('inspect_agents.tools_files._use_typed_results', return_value=True), \
             patch('inspect_agents.tools_files.anyio.fail_after'), \
             patch('inspect_ai.util._store_model.store_as') as mock_store_as:
            
            mock_files = Mock()
            mock_files.get_file.return_value = ""
            mock_store_as.return_value = mock_files
            
            params = FilesParams(root=ReadParams(command="read", file_path="empty.txt"))
            result = await self.tool(params)
            
            assert isinstance(result, FileReadResult)
            assert result.lines == []
            assert "empty contents" in result.summary

    @pytest.mark.asyncio
    async def test_write_command_store_mode(self):
        """Test write command in store mode."""
        with patch('inspect_agents.tools_files._use_sandbox_fs', return_value=False), \
             patch('inspect_agents.tools_files._use_typed_results', return_value=False), \
             patch('inspect_agents.tools_files.anyio.fail_after'), \
             patch('inspect_ai.util._store_model.store_as') as mock_store_as:
            
            mock_files = Mock()
            mock_store_as.return_value = mock_files
            
            params = FilesParams(root=WriteParams(
                command="write",
                file_path="new.txt",
                content="Hello world",
                instance=None
            ))
            result = await self.tool(params)
            
            assert "Updated file new.txt" in result
            mock_files.put_file.assert_called_once_with("new.txt", "Hello world")

    @pytest.mark.asyncio
    async def test_write_command_typed_results(self):
        """Test write command with typed results."""
        with patch('inspect_agents.tools_files._use_sandbox_fs', return_value=False), \
             patch('inspect_agents.tools_files._use_typed_results', return_value=True), \
             patch('inspect_agents.tools_files.anyio.fail_after'), \
             patch('inspect_ai.util._store_model.store_as') as mock_store_as:
            
            mock_files = Mock()
            mock_store_as.return_value = mock_files
            
            params = FilesParams(root=WriteParams(
                command="write",
                file_path="new.txt",
                content="Hello world"
            ))
            result = await self.tool(params)
            
            assert isinstance(result, FileWriteResult)
            assert result.path == "new.txt"
            assert "Updated file" in result.summary

    @pytest.mark.asyncio
    async def test_edit_command_store_mode(self):
        """Test edit command in store mode."""
        with patch('inspect_agents.tools_files._use_sandbox_fs', return_value=False), \
             patch('inspect_agents.tools_files._use_typed_results', return_value=True), \
             patch('inspect_agents.tools_files.anyio.fail_after'), \
             patch('inspect_ai.util._store_model.store_as') as mock_store_as:
            
            mock_files = Mock()
            mock_files.get_file.return_value = "Hello world\nGoodbye world"
            mock_store_as.return_value = mock_files
            
            params = FilesParams(root=EditParams(
                command="edit",
                file_path="edit.txt",
                old_string="world",
                new_string="universe",
                replace_all=False
            ))
            result = await self.tool(params)
            
            assert isinstance(result, FileEditResult)
            assert result.path == "edit.txt"
            assert result.replaced == 1
            mock_files.put_file.assert_called_once_with("edit.txt", "Hello universe\nGoodbye world")

    @pytest.mark.asyncio
    async def test_edit_command_replace_all(self):
        """Test edit command with replace_all=True."""
        with patch('inspect_agents.tools_files._use_sandbox_fs', return_value=False), \
             patch('inspect_agents.tools_files._use_typed_results', return_value=True), \
             patch('inspect_agents.tools_files.anyio.fail_after'), \
             patch('inspect_ai.util._store_model.store_as') as mock_store_as:
            
            mock_files = Mock()
            mock_files.get_file.return_value = "Hello world\nGoodbye world"
            mock_store_as.return_value = mock_files
            
            params = FilesParams(root=EditParams(
                command="edit",
                file_path="edit.txt",
                old_string="world",
                new_string="universe",
                replace_all=True
            ))
            result = await self.tool(params)
            
            assert isinstance(result, FileEditResult)
            assert result.replaced == 2
            mock_files.put_file.assert_called_once_with("edit.txt", "Hello universe\nGoodbye universe")

    @pytest.mark.asyncio
    async def test_edit_command_string_not_found(self):
        """Test edit command when old_string is not found."""
        with patch('inspect_agents.tools_files._use_sandbox_fs', return_value=False), \
             patch('inspect_agents.tools_files.anyio.fail_after'), \
             patch('inspect_ai.util._store_model.store_as') as mock_store_as:
            
            mock_files = Mock()
            mock_files.get_file.return_value = "Hello world"
            mock_store_as.return_value = mock_files
            
            params = FilesParams(root=EditParams(
                command="edit",
                file_path="edit.txt",
                old_string="notfound",
                new_string="replacement"
            ))
            
            with pytest.raises(Exception) as exc_info:
                await self.tool(params)
            assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_sandbox_mode_read(self):
        """Test read command in sandbox mode."""
        with patch('inspect_agents.tools_files._use_sandbox_fs', return_value=True), \
             patch('inspect_agents.tools_files._use_typed_results', return_value=False), \
             patch('inspect_agents.tools_files.anyio.fail_after'), \
             patch('inspect_ai.tool._tools._text_editor.text_editor') as mock_editor_factory:
            
            mock_editor = AsyncMock()
            mock_editor.return_value = "line 1\nline 2"
            mock_editor_factory.return_value = mock_editor
            
            params = FilesParams(root=ReadParams(
                command="read",
                file_path="test.txt",
                offset=0,
                limit=10
            ))
            result = await self.tool(params)
            
            mock_editor.assert_called_once_with(
                command="view",
                path="test.txt",
                view_range=[1, 10]
            )
            assert "     1\tline 1" in result
            assert "     2\tline 2" in result

    def test_params_validation_extra_forbid(self):
        """Test that extra fields are rejected due to extra='forbid'."""
        # This should raise a validation error due to extra="forbid"
        with pytest.raises(Exception):
            FilesParams(root=LsParams(command="ls", extra_field="not_allowed"))

    def test_discriminator_validation(self):
        """Test that discriminator correctly routes to the right type."""
        # Valid discriminated union
        params1 = FilesParams(root={"command": "ls"})
        assert isinstance(params1.root, LsParams)
        
        params2 = FilesParams(root={"command": "read", "file_path": "test.txt"})
        assert isinstance(params2.root, ReadParams)
        
        params3 = FilesParams(root={"command": "write", "file_path": "test.txt", "content": "data"})
        assert isinstance(params3.root, WriteParams)
        
        params4 = FilesParams(
            root={
                "command": "edit",
                "file_path": "test.txt",
                "old_string": "old",
                "new_string": "new",
            }
        )
        assert isinstance(params4.root, EditParams)

    def test_invalid_command_discriminator(self):
        """Test that invalid command values are rejected."""
        with pytest.raises(Exception):
            FilesParams(root={"command": "invalid_command"})


class TestFilesToolIntegration:
    """Integration tests for the unified files tool with real pydantic validation."""

    def test_pydantic_schema_validation(self):
        """Test that Pydantic schemas enforce validation correctly."""
        # Valid params should work
        valid_read = ReadParams(command="read", file_path="test.txt", offset=0, limit=100)
        assert valid_read.command == "read"
        assert valid_read.file_path == "test.txt"
        
        # Missing required fields should fail
        with pytest.raises(Exception):
            ReadParams(command="read")  # Missing file_path
            
        # Wrong types should fail
        with pytest.raises(Exception):
            ReadParams(command="read", file_path="test.txt", offset="not_int")

    def test_base_params_inheritance(self):
        """Test that all command params inherit from BaseFileParams correctly."""
        params = ReadParams(command="read", file_path="test.txt", instance="test_instance")
        assert params.instance == "test_instance"
        
        params2 = LsParams(command="ls", instance=None)
        assert params2.instance is None

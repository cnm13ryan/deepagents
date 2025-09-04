"""Tests for unified files tool with discriminated union."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from inspect_agents.tools_files import (
    DeleteParams,
    EditParams,
    FileDeleteResult,
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
            with (
                patch("inspect_agents.tools_files._use_sandbox_fs", return_value=False),
                patch("inspect_agents.tools_files._use_typed_results", return_value=False),
                patch("inspect_ai.util._store_model.store_as") as mock_store_as,
            ):
                # Mock Files store
                mock_files = Mock()
                mock_files.list_files.return_value = ["file1.txt", "file2.txt"]
                mock_store_as.return_value = mock_files

                params = FilesParams(root=LsParams(command="ls", instance=None))
                result = await self.tool(params)

                assert result == ["file1.txt", "file2.txt"]
                mock_store_as.assert_called_once()
                mock_files.list_files.assert_called_once()

        asyncio.run(_test())

    @pytest.mark.asyncio
    async def test_ls_command_typed_results(self):
        """Test ls command with typed results."""
        with (
            patch("inspect_agents.tools_files._use_sandbox_fs", return_value=False),
            patch("inspect_agents.tools_files._use_typed_results", return_value=True),
            patch("inspect_ai.util._store_model.store_as") as mock_store_as,
        ):
            mock_files = Mock()
            mock_files.list_files.return_value = ["file1.txt", "file2.txt"]
            mock_store_as.return_value = mock_files

            params = FilesParams(root=LsParams(command="ls", instance="test"))
            result = await self.tool(params)

            assert isinstance(result, FileListResult)
            assert result.files == ["file1.txt", "file2.txt"]
            mock_store_as.assert_called_with(mock_store_as.call_args[0][0], instance="test")

    @pytest.mark.asyncio
    async def test_read_command_store_mode(self):
        """Test read command in store mode."""
        with (
            patch("inspect_agents.tools_files._use_sandbox_fs", return_value=False),
            patch("inspect_agents.tools_files._use_typed_results", return_value=False),
            patch("inspect_agents.tools_files.anyio.fail_after"),
            patch("inspect_ai.util._store_model.store_as") as mock_store_as,
        ):
            mock_files = Mock()
            mock_files.get_file.return_value = "line 1\nline 2\nline 3"
            mock_store_as.return_value = mock_files

            params = FilesParams(
                root=ReadParams(command="read", file_path="test.txt", offset=0, limit=2, instance=None)
            )
            result = await self.tool(params)

            # Should format with line numbers
            lines = result.split("\n")
            assert "     1\tline 1" in lines[0]
            assert "     2\tline 2" in lines[1]
            assert len(lines) == 2
            mock_files.get_file.assert_called_once_with("test.txt")

    @pytest.mark.asyncio
    async def test_read_command_file_not_found(self):
        """Test read command when file doesn't exist."""
        with (
            patch("inspect_agents.tools_files._use_sandbox_fs", return_value=False),
            patch("inspect_agents.tools_files.anyio.fail_after"),
            patch("inspect_ai.util._store_model.store_as") as mock_store_as,
        ):
            mock_files = Mock()
            mock_files.get_file.return_value = None
            mock_store_as.return_value = mock_files

            params = FilesParams(root=ReadParams(command="read", file_path="nonexistent.txt"))

            with pytest.raises(Exception) as exc_info:
                await self.tool(params)
            assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_read_command_empty_file(self):
        """Test read command with empty file."""
        with (
            patch("inspect_agents.tools_files._use_sandbox_fs", return_value=False),
            patch("inspect_agents.tools_files._use_typed_results", return_value=True),
            patch("inspect_agents.tools_files.anyio.fail_after"),
            patch("inspect_ai.util._store_model.store_as") as mock_store_as,
        ):
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
        with (
            patch("inspect_agents.tools_files._use_sandbox_fs", return_value=False),
            patch("inspect_agents.tools_files._use_typed_results", return_value=False),
            patch("inspect_agents.tools_files.anyio.fail_after"),
            patch("inspect_ai.util._store_model.store_as") as mock_store_as,
        ):
            mock_files = Mock()
            mock_store_as.return_value = mock_files

            params = FilesParams(
                root=WriteParams(command="write", file_path="new.txt", content="Hello world", instance=None)
            )
            result = await self.tool(params)

            assert "Updated file new.txt" in result
            mock_files.put_file.assert_called_once_with("new.txt", "Hello world")

    @pytest.mark.asyncio
    async def test_write_command_typed_results(self):
        """Test write command with typed results."""
        with (
            patch("inspect_agents.tools_files._use_sandbox_fs", return_value=False),
            patch("inspect_agents.tools_files._use_typed_results", return_value=True),
            patch("inspect_agents.tools_files.anyio.fail_after"),
            patch("inspect_ai.util._store_model.store_as") as mock_store_as,
        ):
            mock_files = Mock()
            mock_store_as.return_value = mock_files

            params = FilesParams(root=WriteParams(command="write", file_path="new.txt", content="Hello world"))
            result = await self.tool(params)

            assert isinstance(result, FileWriteResult)
            assert result.path == "new.txt"
            assert "Updated file" in result.summary

    @pytest.mark.asyncio
    async def test_edit_command_store_mode(self):
        """Test edit command in store mode."""
        with (
            patch("inspect_agents.tools_files._use_sandbox_fs", return_value=False),
            patch("inspect_agents.tools_files._use_typed_results", return_value=True),
            patch("inspect_agents.tools_files.anyio.fail_after"),
            patch("inspect_ai.util._store_model.store_as") as mock_store_as,
        ):
            mock_files = Mock()
            mock_files.get_file.return_value = "Hello world\nGoodbye world"
            mock_store_as.return_value = mock_files

            params = FilesParams(
                root=EditParams(
                    command="edit", file_path="edit.txt", old_string="world", new_string="universe", replace_all=False
                )
            )
            result = await self.tool(params)

            assert isinstance(result, FileEditResult)
            assert result.path == "edit.txt"
            assert result.replaced == 1
            mock_files.put_file.assert_called_once_with("edit.txt", "Hello universe\nGoodbye world")

    @pytest.mark.asyncio
    async def test_edit_command_replace_all(self):
        """Test edit command with replace_all=True."""
        with (
            patch("inspect_agents.tools_files._use_sandbox_fs", return_value=False),
            patch("inspect_agents.tools_files._use_typed_results", return_value=True),
            patch("inspect_agents.tools_files.anyio.fail_after"),
            patch("inspect_ai.util._store_model.store_as") as mock_store_as,
        ):
            mock_files = Mock()
            mock_files.get_file.return_value = "Hello world\nGoodbye world"
            mock_store_as.return_value = mock_files

            params = FilesParams(
                root=EditParams(
                    command="edit", file_path="edit.txt", old_string="world", new_string="universe", replace_all=True
                )
            )
            result = await self.tool(params)

            assert isinstance(result, FileEditResult)
            assert result.replaced == 2
            mock_files.put_file.assert_called_once_with("edit.txt", "Hello universe\nGoodbye universe")

    @pytest.mark.asyncio
    async def test_edit_command_string_not_found(self):
        """Test edit command when old_string is not found."""
        with (
            patch("inspect_agents.tools_files._use_sandbox_fs", return_value=False),
            patch("inspect_agents.tools_files.anyio.fail_after"),
            patch("inspect_ai.util._store_model.store_as") as mock_store_as,
        ):
            mock_files = Mock()
            mock_files.get_file.return_value = "Hello world"
            mock_store_as.return_value = mock_files

            params = FilesParams(
                root=EditParams(command="edit", file_path="edit.txt", old_string="notfound", new_string="replacement")
            )

            with pytest.raises(Exception) as exc_info:
                await self.tool(params)
            assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_command_store_mode_file_exists(self):
        """Test delete command in store mode when file exists."""
        with (
            patch("inspect_agents.tools_files._use_sandbox_fs", return_value=False),
            patch("inspect_agents.tools_files._use_typed_results", return_value=False),
            patch("inspect_agents.tools_files.anyio.fail_after"),
            patch("inspect_ai.util._store_model.store_as") as mock_store_as,
        ):
            mock_files = Mock()
            mock_files.get_file.return_value = "some content"  # File exists
            mock_store_as.return_value = mock_files

            params = FilesParams(root=DeleteParams(command="delete", file_path="test.txt", instance=None))
            result = await self.tool(params)

            assert "Deleted file test.txt" in result
            mock_files.get_file.assert_called_once_with("test.txt")
            mock_files.delete_file.assert_called_once_with("test.txt")

    @pytest.mark.asyncio
    async def test_delete_command_store_mode_file_not_exists(self):
        """Test delete command in store mode when file doesn't exist (idempotent)."""
        with (
            patch("inspect_agents.tools_files._use_sandbox_fs", return_value=False),
            patch("inspect_agents.tools_files._use_typed_results", return_value=False),
            patch("inspect_agents.tools_files.anyio.fail_after"),
            patch("inspect_ai.util._store_model.store_as") as mock_store_as,
        ):
            mock_files = Mock()
            mock_files.get_file.return_value = None  # File doesn't exist
            mock_store_as.return_value = mock_files

            params = FilesParams(root=DeleteParams(command="delete", file_path="nonexistent.txt", instance=None))
            result = await self.tool(params)

            assert "did not exist" in result
            assert "idempotent" in result
            mock_files.get_file.assert_called_once_with("nonexistent.txt")
            mock_files.delete_file.assert_called_once_with("nonexistent.txt")

    @pytest.mark.asyncio
    async def test_delete_command_typed_results_file_exists(self):
        """Test delete command with typed results when file exists."""
        with (
            patch("inspect_agents.tools_files._use_sandbox_fs", return_value=False),
            patch("inspect_agents.tools_files._use_typed_results", return_value=True),
            patch("inspect_agents.tools_files.anyio.fail_after"),
            patch("inspect_ai.util._store_model.store_as") as mock_store_as,
        ):
            mock_files = Mock()
            mock_files.get_file.return_value = "some content"
            mock_store_as.return_value = mock_files

            params = FilesParams(root=DeleteParams(command="delete", file_path="test.txt", instance="test_instance"))
            result = await self.tool(params)

            assert isinstance(result, FileDeleteResult)
            assert result.path == "test.txt"
            assert "Deleted file test.txt" in result.summary
            mock_store_as.assert_called_with(mock_store_as.call_args[0][0], instance="test_instance")

    @pytest.mark.asyncio
    async def test_delete_command_typed_results_file_not_exists(self):
        """Test delete command with typed results when file doesn't exist."""
        with (
            patch("inspect_agents.tools_files._use_sandbox_fs", return_value=False),
            patch("inspect_agents.tools_files._use_typed_results", return_value=True),
            patch("inspect_agents.tools_files.anyio.fail_after"),
            patch("inspect_ai.util._store_model.store_as") as mock_store_as,
        ):
            mock_files = Mock()
            mock_files.get_file.return_value = None
            mock_store_as.return_value = mock_files

            params = FilesParams(root=DeleteParams(command="delete", file_path="nonexistent.txt"))
            result = await self.tool(params)

            assert isinstance(result, FileDeleteResult)
            assert result.path == "nonexistent.txt"
            assert "did not exist" in result.summary
            assert "idempotent" in result.summary

    @pytest.mark.asyncio
    async def test_delete_command_sandbox_mode_unsupported(self):
        """Test delete command in sandbox mode raises appropriate error."""
        with patch("inspect_agents.tools_files._use_sandbox_fs", return_value=True):
            params = FilesParams(root=DeleteParams(command="delete", file_path="test.txt"))

            with pytest.raises(Exception) as exc_info:
                await self.tool(params)
            assert "delete is disabled in sandbox mode" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_sandbox_mode_read(self):
        """Test read command in sandbox mode."""
        with (
            patch("inspect_agents.tools_files._use_sandbox_fs", return_value=True),
            patch("inspect_agents.tools_files._use_typed_results", return_value=True),
            patch("inspect_agents.tools_files.anyio.fail_after"),
        ):
            # Mock bash session to simulate reading file content in sandbox mode
            with patch("inspect_ai.tool._tools._bash_session.bash_session") as mock_bash_session:
                mock_execute = AsyncMock()
                mock_result = Mock()
                mock_result.stdout = "line 1\nline 2\nline 3"
                mock_execute.return_value = mock_result
                mock_bash_session.return_value = mock_execute

                params = FilesParams(root=ReadParams(command="read", file_path="test.txt", offset=0, limit=2))
                result = await self.tool(params)

                # For typed results, verify we get FileReadResult
                assert isinstance(result, FileReadResult)
                assert result.lines == ["1\tline 1", "2\tline 2"]
                assert "file_path" in result.summary

    @pytest.mark.asyncio 
    async def test_parameters_validation(self):
        """Test that parameters validation works correctly for all commands."""
        # Valid write
        valid_write = WriteParams(command="write", file_path="test.txt", content="data")
        assert valid_write.command == "write"
        assert valid_write.file_path == "test.txt"

        # Valid read
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


class TestByteCeilingEnforcement:
    """Test suite for byte ceiling enforcement functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tool = files_tool()

    @pytest.mark.asyncio
    async def test_write_exceeds_byte_ceiling_store_mode(self):
        """Test write command fails when content exceeds byte ceiling."""
        with (
            patch("inspect_agents.tools_files._use_sandbox_fs", return_value=False),
            patch("inspect_agents.tools_files._max_bytes", return_value=100),  # Small limit
            patch("inspect_agents.tools_files.anyio.fail_after"),
        ):
            # Create content that exceeds the 100-byte limit
            large_content = "x" * 150
            params = FilesParams(
                root=WriteParams(command="write", file_path="large.txt", content=large_content)
            )

            with pytest.raises(Exception) as exc_info:
                await self.tool(params)
            assert "exceeds maximum size limit" in str(exc_info.value)
            assert "150 bytes > 100 bytes" in str(exc_info.value)
            assert "INSPECT_AGENTS_FS_MAX_BYTES" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_write_within_byte_ceiling_store_mode(self):
        """Test write command succeeds when content is within byte ceiling."""
        with (
            patch("inspect_agents.tools_files._use_sandbox_fs", return_value=False),
            patch("inspect_agents.tools_files._max_bytes", return_value=100),
            patch("inspect_agents.tools_files._use_typed_results", return_value=False),
            patch("inspect_agents.tools_files.anyio.fail_after"),
            patch("inspect_ai.util._store_model.store_as") as mock_store_as,
        ):
            mock_files = Mock()
            mock_store_as.return_value = mock_files

            small_content = "x" * 50  # Within limit
            params = FilesParams(
                root=WriteParams(command="write", file_path="small.txt", content=small_content)
            )

            result = await self.tool(params)
            assert "Updated file small.txt" in result
            mock_files.put_file.assert_called_once_with("small.txt", small_content)

    @pytest.mark.asyncio
    async def test_edit_exceeds_byte_ceiling_store_mode(self):
        """Test edit command fails when result exceeds byte ceiling."""
        with (
            patch("inspect_agents.tools_files._use_sandbox_fs", return_value=False),
            patch("inspect_agents.tools_files._max_bytes", return_value=100),
            patch("inspect_agents.tools_files.anyio.fail_after"),
            patch("inspect_ai.util._store_model.store_as") as mock_store_as,
        ):
            mock_files = Mock()
            mock_files.get_file.return_value = "Hello world"  # Small original
            mock_store_as.return_value = mock_files

            # Replace "world" with a very long string that makes result exceed limit
            long_replacement = "x" * 200
            params = FilesParams(
                root=EditParams(
                    command="edit", file_path="test.txt", old_string="world", new_string=long_replacement
                )
            )

            with pytest.raises(Exception) as exc_info:
                await self.tool(params)
            assert "exceeding maximum size limit" in str(exc_info.value)
            assert "INSPECT_AGENTS_FS_MAX_BYTES" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_edit_within_byte_ceiling_store_mode(self):
        """Test edit command succeeds when result is within byte ceiling."""
        with (
            patch("inspect_agents.tools_files._use_sandbox_fs", return_value=False),
            patch("inspect_agents.tools_files._max_bytes", return_value=100),
            patch("inspect_agents.tools_files._use_typed_results", return_value=False),
            patch("inspect_agents.tools_files.anyio.fail_after"),
            patch("inspect_ai.util._store_model.store_as") as mock_store_as,
        ):
            mock_files = Mock()
            mock_files.get_file.return_value = "Hello world"
            mock_store_as.return_value = mock_files

            params = FilesParams(
                root=EditParams(command="edit", file_path="test.txt", old_string="world", new_string="universe")
            )

            result = await self.tool(params)
            assert "Updated file test.txt" in result
            mock_files.put_file.assert_called_once_with("test.txt", "Hello universe")

    @pytest.mark.asyncio
    async def test_read_exceeds_byte_ceiling_store_mode(self):
        """Test read command fails when file exceeds byte ceiling."""
        with (
            patch("inspect_agents.tools_files._use_sandbox_fs", return_value=False),
            patch("inspect_agents.tools_files._max_bytes", return_value=100),
            patch("inspect_agents.tools_files.anyio.fail_after"),
            patch("inspect_ai.util._store_model.store_as") as mock_store_as,
        ):
            mock_files = Mock()
            mock_files.get_file.return_value = "x" * 150  # Exceeds limit
            mock_store_as.return_value = mock_files

            params = FilesParams(root=ReadParams(command="read", file_path="large.txt"))

            with pytest.raises(Exception) as exc_info:
                await self.tool(params)
            assert "exceeds maximum size limit" in str(exc_info.value)
            assert "150 bytes > 100 bytes" in str(exc_info.value)
            assert "INSPECT_AGENTS_FS_MAX_BYTES" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_read_within_byte_ceiling_store_mode(self):
        """Test read command succeeds when file is within byte ceiling."""
        with (
            patch("inspect_agents.tools_files._use_sandbox_fs", return_value=False),
            patch("inspect_agents.tools_files._max_bytes", return_value=100),
            patch("inspect_agents.tools_files._use_typed_results", return_value=False),
            patch("inspect_agents.tools_files.anyio.fail_after"),
            patch("inspect_ai.util._store_model.store_as") as mock_store_as,
        ):
            mock_files = Mock()
            mock_files.get_file.return_value = "Hello world"  # Within limit
            mock_store_as.return_value = mock_files

            params = FilesParams(root=ReadParams(command="read", file_path="small.txt"))

            result = await self.tool(params)
            assert "     1\tHello world" in result  # Line numbered format (6 chars padding)

    # Note: Sandbox mode tests are complex to mock due to symlink checks and multiple bash sessions
    # The store mode tests above provide sufficient coverage for the byte ceiling functionality

    @pytest.mark.asyncio  
    async def test_max_bytes_helper_function(self):
        """Test _max_bytes helper function with environment variable."""
        from inspect_agents.tools_files import _max_bytes
        
        with patch.dict("os.environ", {"INSPECT_AGENTS_FS_MAX_BYTES": "1000000"}):
            assert _max_bytes() == 1000000
            
        with patch.dict("os.environ", {}, clear=True):
            # Test default value when env var is not set
            assert _max_bytes() == 5000000
            
        with patch.dict("os.environ", {"INSPECT_AGENTS_FS_MAX_BYTES": "invalid"}):
            # Test fallback to default when env var is invalid
            assert _max_bytes() == 5000000

    @pytest.mark.asyncio
    async def test_unicode_content_byte_calculation(self):
        """Test that byte ceiling correctly handles unicode content."""
        with (
            patch("inspect_agents.tools_files._use_sandbox_fs", return_value=False),
            patch("inspect_agents.tools_files._max_bytes", return_value=6),  # Very small limit
            patch("inspect_agents.tools_files.anyio.fail_after"),
        ):
            # Unicode content that's 2 characters but more bytes
            unicode_content = "🚀🚀"  # Each emoji is 4 bytes in UTF-8 = 8 bytes total
            params = FilesParams(
                root=WriteParams(command="write", file_path="unicode.txt", content=unicode_content)
            )

            with pytest.raises(Exception) as exc_info:
                await self.tool(params)
            assert "exceeds maximum size limit" in str(exc_info.value)
            assert "8 bytes > 6 bytes" in str(exc_info.value)


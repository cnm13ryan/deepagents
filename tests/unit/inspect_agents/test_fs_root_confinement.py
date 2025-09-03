"""Tests for filesystem root confinement in sandbox mode."""

import asyncio
import os
import sys
import types
from unittest.mock import patch

import pytest

from inspect_agents.tools_files import _fs_root, _validate_sandbox_path, files_tool, FilesParams, ReadParams, WriteParams, EditParams, LsParams


class TestFsRootConfinement:
    """Test suite for filesystem root confinement."""

    def test_fs_root_default(self):
        """Test _fs_root() returns default '/repo' when env var not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Clear environment
            if "INSPECT_AGENTS_FS_ROOT" in os.environ:
                del os.environ["INSPECT_AGENTS_FS_ROOT"]
            assert _fs_root() == "/repo"

    def test_fs_root_custom(self):
        """Test _fs_root() returns custom value from env var."""
        with patch.dict(os.environ, {"INSPECT_AGENTS_FS_ROOT": "/custom/path"}):
            assert _fs_root() == "/custom/path"

    def test_fs_root_relative_to_absolute(self):
        """Test _fs_root() converts relative paths to absolute."""
        with patch.dict(os.environ, {"INSPECT_AGENTS_FS_ROOT": "relative/path"}):
            result = _fs_root()
            assert os.path.isabs(result)
            assert result.endswith("relative/path")

    def test_validate_sandbox_path_allowed_absolute(self):
        """Test _validate_sandbox_path() allows paths within root (absolute)."""
        with patch.dict(os.environ, {"INSPECT_AGENTS_FS_ROOT": "/repo"}):
            # Paths within root should be allowed
            assert _validate_sandbox_path("/repo/file.txt") == "/repo/file.txt"
            assert _validate_sandbox_path("/repo/subdir/file.txt") == "/repo/subdir/file.txt"
            assert _validate_sandbox_path("/repo") == "/repo"

    def test_validate_sandbox_path_allowed_relative(self):
        """Test _validate_sandbox_path() allows relative paths within root."""
        with patch.dict(os.environ, {"INSPECT_AGENTS_FS_ROOT": "/repo"}):
            # Relative paths should be joined with root
            assert _validate_sandbox_path("file.txt") == "/repo/file.txt"
            assert _validate_sandbox_path("subdir/file.txt") == "/repo/subdir/file.txt"

    def test_validate_sandbox_path_denied_outside_root(self):
        """Test _validate_sandbox_path() denies paths outside root."""
        with patch.dict(os.environ, {"INSPECT_AGENTS_FS_ROOT": "/repo"}):
            # These paths should be denied
            forbidden_paths = [
                "/etc/passwd",
                "/tmp/file.txt",
                "/repo/../etc/passwd",
                "../../etc/passwd",
            ]
            
            for path in forbidden_paths:
                with pytest.raises(Exception) as exc_info:
                    _validate_sandbox_path(path)
                assert "Access denied" in str(exc_info.value)
                assert "outside the configured filesystem root" in str(exc_info.value)

    def test_validate_sandbox_path_handles_path_traversal(self):
        """Test _validate_sandbox_path() prevents path traversal attacks."""
        with patch.dict(os.environ, {"INSPECT_AGENTS_FS_ROOT": "/repo"}):
            # Path traversal attempts should be denied
            traversal_attempts = [
                "/repo/../etc/passwd",
                "/repo/subdir/../../../etc/passwd",
                "/repo/./../../etc/passwd",
            ]
            
            for path in traversal_attempts:
                with pytest.raises(Exception) as exc_info:
                    _validate_sandbox_path(path)
                assert "Access denied" in str(exc_info.value)

    def test_validate_sandbox_path_normalizes_paths(self):
        """Test _validate_sandbox_path() properly normalizes paths."""
        with patch.dict(os.environ, {"INSPECT_AGENTS_FS_ROOT": "/repo"}):
            # These should be normalized and allowed
            assert _validate_sandbox_path("/repo/./file.txt") == "/repo/file.txt"
            assert _validate_sandbox_path("/repo/subdir/../file.txt") == "/repo/file.txt"


def _install_editor_stub_with_validation(fs: dict[str, str]):
    """Install editor stub that respects path validation."""
    mod_name = "inspect_ai.tool._tools._text_editor"
    if mod_name in sys.modules:
        del sys.modules[mod_name]

    mod = types.ModuleType(mod_name)

    from inspect_ai.tool._tool import Tool, tool

    @tool()
    def text_editor() -> Tool:  # type: ignore[return-type]
        async def execute(
            command: str,
            path: str,
            file_text: str | None = None,
            insert_line: int | None = None,
            new_str: str | None = None,
            old_str: str | None = None,
            view_range: list[int] | None = None,
        ) -> str:
            if command == "create":
                fs[path] = file_text or ""
                return "OK"
            elif command == "view":
                content = fs.get(path, "")
                if view_range is None:
                    return content
                start, end = view_range
                lines = content.splitlines()
                s = max(1, start) - 1
                e = len(lines) if end == -1 else min(len(lines), end)
                return "\n".join(lines[s:e])
            elif command == "str_replace":
                content = fs.get(path, None)
                if content is None:
                    return "ERR"
                fs[path] = content.replace(old_str or "", new_str or "")
                return "OK"
            else:
                return "UNSUPPORTED"

        return execute

    mod.text_editor = text_editor
    sys.modules[mod_name] = mod


def _install_bash_stub_with_root(fs: dict[str, str]):
    """Install bash stub that accepts root parameter for ls."""
    mod_name = "inspect_ai.tool._tools._bash_session"
    if mod_name in sys.modules:
        del sys.modules[mod_name]

    mod = types.ModuleType(mod_name)

    from inspect_ai.tool._tool import Tool, tool

    class MockResult:
        def __init__(self, stdout: str):
            self.stdout = stdout

    @tool()
    def bash_session() -> Tool:  # type: ignore[return-type]
        async def execute(action: str, command: str | None = None) -> MockResult:
            if action == "run" and command and command.startswith("ls -1"):
                # Handle both quoted and unquoted paths
                if "'/repo'" in command or '"/repo"' in command or command.endswith("/repo"):
                    # Return files from the dict as a newline-separated list
                    file_list = list(fs.keys())
                    return MockResult("\n".join(file_list))
                else:
                    # For other roots, return empty or error
                    return MockResult("")
            else:
                return MockResult("")

        return execute

    mod.bash_session = bash_session
    sys.modules[mod_name] = mod


class TestSandboxPathValidationIntegration:
    """Integration tests for path validation in sandbox mode."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tool = files_tool()

    def test_sandbox_read_allowed_path(self, monkeypatch):
        """Test read operation allows paths within configured root."""
        monkeypatch.setenv("INSPECT_AGENTS_FS_MODE", "sandbox")
        monkeypatch.setenv("INSPECT_AGENTS_FS_ROOT", "/repo")
        
        fs: dict[str, str] = {"/repo/allowed.txt": "content"}
        _install_editor_stub_with_validation(fs)

        async def test():
            params = FilesParams(root=ReadParams(command="read", file_path="/repo/allowed.txt"))
            result = await self.tool(params)
            return result

        result = asyncio.run(test())
        assert "content" in result

    def test_sandbox_read_denied_path(self, monkeypatch):
        """Test read operation denies paths outside configured root."""
        monkeypatch.setenv("INSPECT_AGENTS_FS_MODE", "sandbox")
        monkeypatch.setenv("INSPECT_AGENTS_FS_ROOT", "/repo")
        
        fs: dict[str, str] = {}
        _install_editor_stub_with_validation(fs)

        async def test():
            params = FilesParams(root=ReadParams(command="read", file_path="/etc/passwd"))
            with pytest.raises(Exception) as exc_info:
                await self.tool(params)
            return str(exc_info.value)

        error_msg = asyncio.run(test())
        assert "Access denied" in error_msg
        assert "outside the configured filesystem root" in error_msg

    def test_sandbox_write_allowed_path(self, monkeypatch):
        """Test write operation allows paths within configured root."""
        monkeypatch.setenv("INSPECT_AGENTS_FS_MODE", "sandbox")
        monkeypatch.setenv("INSPECT_AGENTS_FS_ROOT", "/repo")
        
        fs: dict[str, str] = {}
        _install_editor_stub_with_validation(fs)

        async def test():
            params = FilesParams(root=WriteParams(
                command="write", 
                file_path="/repo/new.txt", 
                content="test content"
            ))
            result = await self.tool(params)
            return result

        result = asyncio.run(test())
        assert "Updated file" in result

    def test_sandbox_write_denied_path(self, monkeypatch):
        """Test write operation denies paths outside configured root."""
        monkeypatch.setenv("INSPECT_AGENTS_FS_MODE", "sandbox")
        monkeypatch.setenv("INSPECT_AGENTS_FS_ROOT", "/repo")
        
        fs: dict[str, str] = {}
        _install_editor_stub_with_validation(fs)

        async def test():
            params = FilesParams(root=WriteParams(
                command="write", 
                file_path="/tmp/malicious.txt", 
                content="bad content"
            ))
            with pytest.raises(Exception) as exc_info:
                await self.tool(params)
            return str(exc_info.value)

        error_msg = asyncio.run(test())
        assert "Access denied" in error_msg

    def test_sandbox_edit_allowed_path(self, monkeypatch):
        """Test edit operation allows paths within configured root."""
        monkeypatch.setenv("INSPECT_AGENTS_FS_MODE", "sandbox")
        monkeypatch.setenv("INSPECT_AGENTS_FS_ROOT", "/repo")
        
        fs: dict[str, str] = {"/repo/edit.txt": "hello world"}
        _install_editor_stub_with_validation(fs)

        async def test():
            params = FilesParams(root=EditParams(
                command="edit",
                file_path="/repo/edit.txt",
                old_string="hello",
                new_string="hi"
            ))
            result = await self.tool(params)
            return result

        result = asyncio.run(test())
        assert "Updated file" in result

    def test_sandbox_edit_denied_path(self, monkeypatch):
        """Test edit operation denies paths outside configured root."""
        monkeypatch.setenv("INSPECT_AGENTS_FS_MODE", "sandbox")
        monkeypatch.setenv("INSPECT_AGENTS_FS_ROOT", "/repo")
        
        fs: dict[str, str] = {}
        _install_editor_stub_with_validation(fs)

        async def test():
            params = FilesParams(root=EditParams(
                command="edit",
                file_path="/etc/hosts",
                old_string="localhost",
                new_string="malicious"
            ))
            with pytest.raises(Exception) as exc_info:
                await self.tool(params)
            return str(exc_info.value)

        error_msg = asyncio.run(test())
        assert "Access denied" in error_msg

    def test_sandbox_ls_uses_configured_root(self, monkeypatch):
        """Test ls operation uses configured root directory."""
        monkeypatch.setenv("INSPECT_AGENTS_FS_MODE", "sandbox")
        monkeypatch.setenv("INSPECT_AGENTS_FS_ROOT", "/repo")
        
        fs: dict[str, str] = {"file1.txt": "content1", "file2.txt": "content2"}
        _install_editor_stub_with_validation(fs)
        _install_bash_stub_with_root(fs)

        async def test():
            params = FilesParams(root=LsParams(command="ls"))
            result = await self.tool(params)
            return result

        result = asyncio.run(test())
        assert isinstance(result, list)
        assert set(result) == {"file1.txt", "file2.txt"}

    def test_sandbox_path_traversal_prevention(self, monkeypatch):
        """Test that path traversal attacks are prevented."""
        monkeypatch.setenv("INSPECT_AGENTS_FS_MODE", "sandbox")
        monkeypatch.setenv("INSPECT_AGENTS_FS_ROOT", "/repo")
        
        fs: dict[str, str] = {}
        _install_editor_stub_with_validation(fs)

        # Test various path traversal attempts
        traversal_paths = [
            "/repo/../etc/passwd",
            "/repo/subdir/../../../etc/passwd",
            "../../etc/passwd",
        ]

        for path in traversal_paths:
            async def test_path():
                params = FilesParams(root=ReadParams(command="read", file_path=path))
                with pytest.raises(Exception) as exc_info:
                    await self.tool(params)
                return str(exc_info.value)

            error_msg = asyncio.run(test_path())
            assert "Access denied" in error_msg

    def test_sandbox_relative_path_handling(self, monkeypatch):
        """Test that relative paths are properly handled within root."""
        monkeypatch.setenv("INSPECT_AGENTS_FS_MODE", "sandbox")
        monkeypatch.setenv("INSPECT_AGENTS_FS_ROOT", "/repo")
        
        fs: dict[str, str] = {"/repo/relative.txt": "relative content"}
        _install_editor_stub_with_validation(fs)

        async def test():
            # Relative path should be joined with root
            params = FilesParams(root=ReadParams(command="read", file_path="relative.txt"))
            result = await self.tool(params)
            return result

        result = asyncio.run(test())
        assert "relative content" in result

    def test_store_mode_unaffected_by_path_validation(self, monkeypatch):
        """Test that store mode is unaffected by path validation."""
        # Force store mode
        monkeypatch.setenv("INSPECT_AGENTS_FS_MODE", "store")
        monkeypatch.setenv("INSPECT_AGENTS_FS_ROOT", "/repo")

        async def test():
            # In store mode, any path should work (no validation)
            with (
                patch("inspect_agents.tools_files.anyio.fail_after"),
                patch("inspect_ai.util._store_model.store_as") as mock_store_as,
            ):
                mock_files = type("MockFiles", (), {})()
                mock_files.get_file = lambda path: "store content"
                mock_store_as.return_value = mock_files

                params = FilesParams(root=ReadParams(command="read", file_path="/etc/passwd"))
                result = await self.tool(params)
                return result

        result = asyncio.run(test())
        assert "store content" in result
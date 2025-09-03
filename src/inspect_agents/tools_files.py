"""Unified files tool with discriminated union pattern.

This module provides a single files_tool() that handles all file operations
using a discriminated union for commands: ls, read, write, edit.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Annotated, Literal

import anyio
from pydantic import BaseModel, Discriminator, Field, RootModel

if TYPE_CHECKING:  # pragma: no cover
    from inspect_ai.tool._tool import Tool

from .state import Files


# Forward declare ToolException to avoid circular imports
# This will be overridden by the import at runtime
class ToolException(Exception):  # noqa: N818
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


# Helper functions
def _use_sandbox_fs() -> bool:
    """Return True if using sandbox filesystem mode."""
    return os.getenv("INSPECT_AGENTS_FS_MODE", "store").strip().lower() == "sandbox"


def _default_tool_timeout() -> float:
    """Get default tool timeout from environment."""
    try:
        return float(os.getenv("INSPECT_AGENTS_TOOL_TIMEOUT", "15"))
    except Exception:
        return 15.0


def _use_typed_results() -> bool:
    """Return True if typed result models should be returned."""
    env_val = os.getenv("INSPECT_AGENTS_TYPED_RESULTS")
    if env_val is None:
        return False
    return env_val.strip().lower() in {"1", "true", "yes", "on"}


# Result types
class FileReadResult(BaseModel):
    """Typed result for read operations."""

    lines: list[str]
    summary: str


class FileWriteResult(BaseModel):
    """Typed result for write operations."""

    path: str
    summary: str


class FileEditResult(BaseModel):
    """Typed result for edit operations."""

    path: str
    replaced: int
    summary: str


class FileDeleteResult(BaseModel):
    """Typed result for delete operations."""

    path: str
    summary: str


class FileListResult(BaseModel):
    """Typed result for ls operations."""

    files: list[str]


# Parameter schemas for each command
class BaseFileParams(BaseModel):
    """Base parameters for all file operations."""

    instance: str | None = Field(None, description="Optional Files instance for isolation")

    class Config:
        extra = "forbid"


class LsParams(BaseFileParams):
    """Parameters for ls command."""

    command: Literal["ls"] = "ls"


class ReadParams(BaseFileParams):
    """Parameters for read command."""

    command: Literal["read"] = "read"
    file_path: str = Field(description="Path to read")
    offset: int = Field(0, description="Line offset (0-based)")
    limit: int = Field(2000, description="Max lines to return")


class WriteParams(BaseFileParams):
    """Parameters for write command."""

    command: Literal["write"] = "write"
    file_path: str = Field(description="Path to write")
    content: str = Field(description="Content to write")


class EditParams(BaseFileParams):
    """Parameters for edit command."""

    command: Literal["edit"] = "edit"
    file_path: str = Field(description="Path to edit")
    old_string: str = Field(description="String to replace")
    new_string: str = Field(description="Replacement string")
    replace_all: bool = Field(False, description="Replace all occurrences if true")


class DeleteParams(BaseFileParams):
    """Parameters for delete command."""

    command: Literal["delete"] = "delete"
    file_path: str = Field(description="Path to delete")


class FilesParams(RootModel):
    """Discriminated union of all file operation parameters."""

    root: Annotated[
        LsParams | ReadParams | WriteParams | EditParams | DeleteParams,
        Discriminator("command"),
    ]


# Execution functions (can be used by wrapper tools)
async def execute_ls(params: LsParams) -> list[str] | FileListResult:
    """Execute ls command."""
    from inspect_ai.util._store_model import store_as

    # Import lazily to avoid circular import during module import
    from .tools import _log_tool_event

    _t0 = _log_tool_event(
        name="files:ls",
        phase="start",
        args={"instance": params.instance},
    )
    files = store_as(Files, instance=params.instance)
    file_list = files.list_files()

    if _use_typed_results():
        return FileListResult(files=file_list)
    _log_tool_event(
        name="files:ls",
        phase="end",
        extra={"ok": True, "count": len(file_list) if isinstance(file_list, list) else len(file_list.files)},
        t0=_t0,
    )
    return file_list


async def execute_read(params: ReadParams) -> str | FileReadResult:
    """Execute read command."""
    from inspect_ai.util._store_model import store_as

    from .tools import _log_tool_event

    _t0 = _log_tool_event(
        name="files:read",
        phase="start",
        args={
            "file_path": params.file_path,
            "offset": params.offset,
            "limit": params.limit,
            "instance": params.instance,
        },
    )

    def _format_lines(content_lines: list[str], start_line_num: int = 1) -> tuple[list[str], str]:
        """Format lines with numbering and return both list and joined string."""
        out_lines: list[str] = []
        ln = start_line_num
        for line_content in content_lines:
            if len(line_content) > 2000:
                line_content = line_content[:2000]
            formatted_line = f"{ln:6d}\t{line_content}"
            out_lines.append(formatted_line)
            ln += 1
        return out_lines, "\n".join(out_lines)

    empty_message = "System reminder: File exists but has empty contents"

    # Sandbox FS mode: call text_editor('view', ...) then format lines
    if _use_sandbox_fs():
        try:
            from inspect_ai.tool._tools._text_editor import text_editor

            editor = text_editor()
            start_line = max(1, int(params.offset) + 1)
            if params.limit is None or params.limit <= 0:
                view_range = [start_line, -1]
            else:
                view_range = [start_line, start_line + int(params.limit) - 1]
            with anyio.fail_after(_default_tool_timeout()):
                raw = await editor(
                    command="view",
                    path=params.file_path,
                    view_range=view_range,
                )
            if raw is None or str(raw).strip() == "":
                if _use_typed_results():
                    _log_tool_event(name="files:read", phase="end", extra={"ok": True, "lines": 0}, t0=_t0)
                    return FileReadResult(lines=[], summary=empty_message)
                _log_tool_event(name="files:read", phase="end", extra={"ok": True, "lines": 0}, t0=_t0)
                return empty_message

            lines = str(raw).splitlines()
            formatted_lines, joined_output = _format_lines(lines, start_line)

            if _use_typed_results():
                _log_tool_event(
                    name="files:read",
                    phase="end",
                    extra={"ok": True, "lines": len(formatted_lines)},
                    t0=_t0,
                )
                return FileReadResult(
                    lines=formatted_lines,
                    summary=f"Read {len(formatted_lines)} lines from {params.file_path} (sandbox mode)",
                )
            _log_tool_event(name="files:read", phase="end", extra={"ok": True, "lines": len(formatted_lines)}, t0=_t0)
            return joined_output
        except Exception:
            # Graceful fallback to store-backed mode
            pass

    # Store-backed with timeout guard
    with anyio.fail_after(_default_tool_timeout()):
        files = store_as(Files, instance=params.instance)
        content = files.get_file(params.file_path)
    if content is None:
        # Import here to use the same ToolException as the tools module
        try:
            from inspect_tool_support._util.common_types import ToolException as _ToolException
        except ImportError:
            _ToolException = ToolException  # noqa: N806
        _log_tool_event(
            name="files:read",
            phase="error",
            extra={"ok": False, "error": "FileNotFound"},
            t0=_t0,
        )
        raise _ToolException(  # noqa: N806
            f"File '{params.file_path}' not found. Please check the file path and ensure the file exists."
        )

    if not content or content.strip() == "":
        if _use_typed_results():
            _log_tool_event(name="files:read", phase="end", extra={"ok": True, "lines": 0}, t0=_t0)
            return FileReadResult(lines=[], summary=empty_message)
        _log_tool_event(name="files:read", phase="end", extra={"ok": True, "lines": 0}, t0=_t0)
        return empty_message

    lines = content.splitlines()
    start_idx = params.offset
    end_idx = min(start_idx + params.limit, len(lines))

    if start_idx >= len(lines):
        try:
            from inspect_tool_support._util.common_types import ToolException as _ToolException
        except ImportError:
            _ToolException = ToolException  # noqa: N806
        raise _ToolException(  # noqa: N806
            f"Line offset {params.offset} exceeds file length ({len(lines)} lines). "
            f"Use an offset between 0 and {len(lines) - 1}."
        )

    selected_lines = lines[start_idx:end_idx]
    # Format with correct line numbers starting from offset + 1
    formatted_lines, joined_output = _format_lines(selected_lines, start_idx + 1)

    if _use_typed_results():
        _log_tool_event(name="files:read", phase="end", extra={"ok": True, "lines": len(formatted_lines)}, t0=_t0)
        return FileReadResult(
            lines=formatted_lines,
            summary=(
                f"Read {len(formatted_lines)} lines from {params.file_path} "
                f"(lines {start_idx + 1}-{start_idx + len(formatted_lines)})"
            ),
        )
    _log_tool_event(name="files:read", phase="end", extra={"ok": True, "lines": len(formatted_lines)}, t0=_t0)
    return joined_output


async def execute_write(params: WriteParams) -> str | FileWriteResult:
    """Execute write command."""
    from inspect_ai.util._store_model import store_as

    from .tools import _log_tool_event

    _t0 = _log_tool_event(
        name="files:write",
        phase="start",
        args={"file_path": params.file_path, "content": params.content, "instance": params.instance},
    )
    summary = f"Updated file {params.file_path}"

    if _use_sandbox_fs():
        try:
            from inspect_ai.tool._tools._text_editor import text_editor

            editor = text_editor()
            with anyio.fail_after(_default_tool_timeout()):
                await editor(command="create", path=params.file_path, file_text=params.content)

            if _use_typed_results():
                _log_tool_event(name="files:write", phase="end", extra={"ok": True}, t0=_t0)
                return FileWriteResult(path=params.file_path, summary=summary + " (sandbox mode)")
            _log_tool_event(name="files:write", phase="end", extra={"ok": True}, t0=_t0)
            return summary
        except Exception:
            pass

    # Store-backed with timeout guard
    with anyio.fail_after(_default_tool_timeout()):
        files = store_as(Files, instance=params.instance)
        files.put_file(params.file_path, params.content)

    if _use_typed_results():
        _log_tool_event(name="files:write", phase="end", extra={"ok": True}, t0=_t0)
        return FileWriteResult(path=params.file_path, summary=summary)
    _log_tool_event(name="files:write", phase="end", extra={"ok": True}, t0=_t0)
    return summary


async def execute_edit(params: EditParams) -> str | FileEditResult:
    """Execute edit command."""
    from inspect_ai.util._store_model import store_as

    from .tools import _log_tool_event

    _t0 = _log_tool_event(
        name="files:edit",
        phase="start",
        args={
            "file_path": params.file_path,
            "old_string": params.old_string,
            "new_string": params.new_string,
            "replace_all": params.replace_all,
            "instance": params.instance,
        },
    )
    # For sandbox mode, we can't easily determine replacement count
    if _use_sandbox_fs():
        try:
            from inspect_ai.tool._tools._text_editor import text_editor

            editor = text_editor()
            with anyio.fail_after(_default_tool_timeout()):
                await editor(
                    command="str_replace",
                    path=params.file_path,
                    old_str=params.old_string,
                    new_str=params.new_string,
                )

            summary = f"Updated file {params.file_path} (sandbox mode)"
            if _use_typed_results():
                # In sandbox mode, we don't know exact replacement count
                _log_tool_event(name="files:edit", phase="end", extra={"ok": True, "replaced": 1}, t0=_t0)
                return FileEditResult(path=params.file_path, replaced=1, summary=summary)
            _log_tool_event(name="files:edit", phase="end", extra={"ok": True, "replaced": 1}, t0=_t0)
            return summary
        except Exception:
            pass

    # Store-backed with timeout guard
    with anyio.fail_after(_default_tool_timeout()):
        files = store_as(Files, instance=params.instance)
        content = files.get_file(params.file_path)
    if content is None:
        # Import here to use the same ToolException as the tools module
        try:
            from inspect_tool_support._util.common_types import ToolException as _ToolException
        except ImportError:
            _ToolException = ToolException  # noqa: N806
        _log_tool_event(
            name="files:edit",
            phase="error",
            extra={"ok": False, "error": "FileNotFound"},
            t0=_t0,
        )
        raise _ToolException(  # noqa: N806
            f"File '{params.file_path}' not found. Please check the file path and ensure the file exists."
        )

    if params.old_string not in content:
        try:
            from inspect_tool_support._util.common_types import ToolException as _ToolException
        except ImportError:
            _ToolException = ToolException  # noqa: N806
        _log_tool_event(
            name="files:edit",
            phase="error",
            extra={"ok": False, "error": "StringNotFound"},
            t0=_t0,
        )
        raise _ToolException(
            f"String '{params.old_string}' not found in file '{params.file_path}'. "
            f"Please check the exact text to replace."
        )

    # Count replacements for accurate reporting
    if params.replace_all:
        replacement_count = content.count(params.old_string)
        updated = content.replace(params.old_string, params.new_string)
    else:
        replacement_count = 1
        updated = content.replace(params.old_string, params.new_string, 1)

    files.put_file(params.file_path, updated)

    summary = f"Updated file {params.file_path}"
    if _use_typed_results():
        _log_tool_event(name="files:edit", phase="end", extra={"ok": True, "replaced": replacement_count}, t0=_t0)
        return FileEditResult(path=params.file_path, replaced=replacement_count, summary=summary)
    _log_tool_event(name="files:edit", phase="end", extra={"ok": True, "replaced": replacement_count}, t0=_t0)
    return summary


async def execute_delete(params: DeleteParams) -> str | FileDeleteResult:
    """Execute delete command."""
    from inspect_ai.util._store_model import store_as

    from .tools import _log_tool_event

    _t0 = _log_tool_event(
        name="files:delete",
        phase="start",
        args={"file_path": params.file_path, "instance": params.instance},
    )

    # Sandbox mode: not supported yet
    if _use_sandbox_fs():
        # Import here to use the same ToolException as the tools module
        try:
            from inspect_tool_support._util.common_types import ToolException as _ToolException
        except ImportError:
            _ToolException = ToolException  # noqa: N806
        _log_tool_event(
            name="files:delete",
            phase="error",
            extra={"ok": False, "error": "SandboxUnsupported"},
            t0=_t0,
        )
        raise _ToolException("delete unsupported in sandbox mode")

    # Store-backed with timeout guard
    with anyio.fail_after(_default_tool_timeout()):
        files = store_as(Files, instance=params.instance)
        # Check if file exists before deletion for proper messaging
        file_exists = files.get_file(params.file_path) is not None
        files.delete_file(params.file_path)

    if file_exists:
        summary = f"Deleted file {params.file_path}"
    else:
        summary = f"File {params.file_path} did not exist (delete operation was idempotent)"

    if _use_typed_results():
        _log_tool_event(name="files:delete", phase="end", extra={"ok": True, "existed": file_exists}, t0=_t0)
        return FileDeleteResult(path=params.file_path, summary=summary)
    _log_tool_event(name="files:delete", phase="end", extra={"ok": True, "existed": file_exists}, t0=_t0)
    return summary


# The main files tool
def files_tool():  # -> Tool
    """Unified files tool using discriminated union for commands.

    Supports commands: ls, read, write, edit, delete
    """
    # Local imports to avoid executing inspect_ai.tool __init__ during module import
    from inspect_ai.tool._tool import tool
    from inspect_ai.tool._tool_def import ToolDef
    from inspect_ai.tool._tool_params import ToolParams
    from inspect_ai.util._json import json_schema

    @tool
    def _factory() -> Tool:
        async def execute(
            params: FilesParams,
        ) -> str | FileListResult | FileReadResult | FileWriteResult | FileEditResult | FileDeleteResult:
            # Add Pydantic validation layer for early error detection
            try:
                from .tool_types import FilesToolParams

                # Validate input using our stricter Pydantic model before proceeding
                if hasattr(params, "root") and hasattr(params.root, "model_dump"):
                    raw_dict = params.root.model_dump()
                else:
                    # Fallback for dict inputs
                    raw_dict = params if isinstance(params, dict) else params.root

                # This will raise ValidationError with clear message if unknown fields are present
                FilesToolParams.model_validate(raw_dict)
            except ImportError:
                # If tool_types not available, skip validation
                pass
            except Exception as e:
                # Import here to use the same ToolException as the tools module
                try:
                    from inspect_tool_support._util.common_types import ToolException as _ToolException
                except ImportError:
                    _ToolException = ToolException  # noqa: N806
                raise _ToolException(f"Invalid parameters: {str(e)}")

            command_params = params.root

            if isinstance(command_params, LsParams):
                return await execute_ls(command_params)
            elif isinstance(command_params, ReadParams):
                return await execute_read(command_params)
            elif isinstance(command_params, WriteParams):
                return await execute_write(command_params)
            elif isinstance(command_params, EditParams):
                return await execute_edit(command_params)
            elif isinstance(command_params, DeleteParams):
                return await execute_delete(command_params)
            else:
                try:
                    from inspect_tool_support._util.common_types import ToolException as _ToolException
                except ImportError:
                    _ToolException = ToolException  # noqa: N806
                raise _ToolException(f"Unknown command type: {type(command_params)}")

        params = ToolParams()
        params.properties["params"] = json_schema(FilesParams)
        params.properties["params"].description = "File operation parameters with discriminated union"
        params.required.append("params")

        return ToolDef(
            execute,
            name="files",
            description="Unified file operations tool (ls, read, write, edit, delete).",
            parameters=params,
        ).as_tool()

    return _factory()

"""Unified files tool with discriminated union pattern.

This module provides a single files_tool() that handles all file operations
using a discriminated union for commands: ls, read, write, edit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal, Union
import os
import anyio
from pydantic import BaseModel, Discriminator, Field, RootModel

if TYPE_CHECKING:  # pragma: no cover
    from inspect_ai.tool._tool import Tool
    from inspect_ai.tool._tool_def import ToolDef
    from inspect_ai.tool._tool_params import ToolParams
    from inspect_ai.util._json import json_schema

from .state import Files

# Forward declare ToolException to avoid circular imports
# This will be overridden by the import at runtime
class ToolException(Exception):
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


class FilesParams(RootModel):
    """Discriminated union of all file operation parameters."""
    root: Annotated[
        Union[LsParams, ReadParams, WriteParams, EditParams],
        Discriminator("command"),
    ]


# Execution functions (can be used by wrapper tools)
async def execute_ls(params: LsParams) -> list[str] | FileListResult:
    """Execute ls command."""
    from inspect_ai.util._store_model import store_as
    
    files = store_as(Files, instance=params.instance)
    file_list = files.list_files()
    
    if _use_typed_results():
        return FileListResult(files=file_list)
    return file_list


async def execute_read(params: ReadParams) -> str | FileReadResult:
    """Execute read command."""
    from inspect_ai.util._store_model import store_as
    
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
                    return FileReadResult(lines=[], summary=empty_message)
                return empty_message
            
            lines = str(raw).splitlines()
            formatted_lines, joined_output = _format_lines(lines, start_line)
            
            if _use_typed_results():
                return FileReadResult(
                    lines=formatted_lines,
                    summary=f"Read {len(formatted_lines)} lines from {params.file_path} (sandbox mode)"
                )
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
            _ToolException = ToolException
        raise _ToolException(f"File '{params.file_path}' not found. Please check the file path and ensure the file exists.")

    if not content or content.strip() == "":
        if _use_typed_results():
            return FileReadResult(lines=[], summary=empty_message)
        return empty_message

    lines = content.splitlines()
    start_idx = params.offset
    end_idx = min(start_idx + params.limit, len(lines))

    if start_idx >= len(lines):
        try:
            from inspect_tool_support._util.common_types import ToolException as _ToolException
        except ImportError:
            _ToolException = ToolException
        raise _ToolException(f"Line offset {params.offset} exceeds file length ({len(lines)} lines). Use an offset between 0 and {len(lines)-1}.")

    selected_lines = lines[start_idx:end_idx]
    # Format with correct line numbers starting from offset + 1
    formatted_lines, joined_output = _format_lines(selected_lines, start_idx + 1)
    
    if _use_typed_results():
        return FileReadResult(
            lines=formatted_lines,
            summary=f"Read {len(formatted_lines)} lines from {params.file_path} (lines {start_idx+1}-{start_idx+len(formatted_lines)})"
        )
    return joined_output


async def execute_write(params: WriteParams) -> str | FileWriteResult:
    """Execute write command."""
    from inspect_ai.util._store_model import store_as
    
    summary = f"Updated file {params.file_path}"
    
    if _use_sandbox_fs():
        try:
            from inspect_ai.tool._tools._text_editor import text_editor
            editor = text_editor()
            with anyio.fail_after(_default_tool_timeout()):
                await editor(command="create", path=params.file_path, file_text=params.content)
            
            if _use_typed_results():
                return FileWriteResult(path=params.file_path, summary=summary + " (sandbox mode)")
            return summary
        except Exception:
            pass
    
    # Store-backed with timeout guard
    with anyio.fail_after(_default_tool_timeout()):
        files = store_as(Files, instance=params.instance)
        files.put_file(params.file_path, params.content)
    
    if _use_typed_results():
        return FileWriteResult(path=params.file_path, summary=summary)
    return summary


async def execute_edit(params: EditParams) -> str | FileEditResult:
    """Execute edit command."""
    from inspect_ai.util._store_model import store_as
    
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
                return FileEditResult(path=params.file_path, replaced=1, summary=summary)
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
            _ToolException = ToolException
        raise _ToolException(f"File '{params.file_path}' not found. Please check the file path and ensure the file exists.")

    if params.old_string not in content:
        try:
            from inspect_tool_support._util.common_types import ToolException as _ToolException
        except ImportError:
            _ToolException = ToolException
        raise _ToolException(f"String '{params.old_string}' not found in file '{params.file_path}'. Please check the exact text to replace.")

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
        return FileEditResult(path=params.file_path, replaced=replacement_count, summary=summary)
    return summary


# The main files tool
def files_tool():  # -> Tool
    """Unified files tool using discriminated union for commands.
    
    Supports commands: ls, read, write, edit
    """
    # Local imports to avoid executing inspect_ai.tool __init__ during module import
    from inspect_ai.tool._tool import Tool, tool
    from inspect_ai.tool._tool_def import ToolDef
    from inspect_ai.tool._tool_params import ToolParams
    from inspect_ai.util._json import json_schema
    from inspect_ai.util._store_model import store_as

    @tool
    def _factory() -> Tool:
        async def execute(params: FilesParams) -> str | FileListResult | FileReadResult | FileWriteResult | FileEditResult:
            command_params = params.root
            
            if isinstance(command_params, LsParams):
                return await execute_ls(command_params)
            elif isinstance(command_params, ReadParams):
                return await execute_read(command_params)
            elif isinstance(command_params, WriteParams):
                return await execute_write(command_params)
            elif isinstance(command_params, EditParams):
                return await execute_edit(command_params)
            else:
                try:
                    from inspect_tool_support._util.common_types import ToolException as _ToolException
                except ImportError:
                    _ToolException = ToolException
                raise _ToolException(f"Unknown command type: {type(command_params)}")

        params = ToolParams()
        params.properties["params"] = json_schema(FilesParams)
        params.properties["params"].description = "File operation parameters with discriminated union"
        params.required.append("params")

        return ToolDef(
            execute,
            name="files",
            description="Unified file operations tool (ls, read, write, edit).",
            parameters=params,
        ).as_tool()

    return _factory()
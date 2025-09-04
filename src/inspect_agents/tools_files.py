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

# --- Sandbox preflight (cached) ------------------------------------------------
_SANDBOX_READY: bool | None = None
_SANDBOX_WARN: str | None = None


async def _ensure_sandbox_ready(tool_name: str) -> bool:
    """Return True if the Inspect sandbox service is available.

    Uses Inspect's `tool_support_sandbox` helper to verify that the
    `inspect-tool-support` service exists in the configured sandbox. On
    failure, caches a warning string so subsequent calls short‑circuit and
    callers can gracefully fall back to the Store-backed filesystem.

    This check runs at first use only and is safe in unit tests that stub
    tool modules: if the helper isn't importable, we assume sandbox is not
    available and prefer a safe fallback rather than raising.
    """
    global _SANDBOX_READY, _SANDBOX_WARN
    if _SANDBOX_READY is not None:
        return _SANDBOX_READY

    # Special-case: if tests have installed in-process stubs for tools,
    # treat sandbox as available. This enables unit tests without Docker.
    try:
        import sys

        if tool_name == "editor" and "inspect_ai.tool._tools._text_editor" in sys.modules:
            _SANDBOX_READY = True
            return True
        if tool_name == "bash session" and "inspect_ai.tool._tools._bash_session" in sys.modules:
            _SANDBOX_READY = True
            return True
    except Exception:
        pass

    # Lazy import to avoid heavy deps when not in sandbox mode
    try:  # pragma: no cover - import paths exercised by integration tests
        from inspect_ai.tool._tool_support_helpers import tool_support_sandbox
    except Exception:
        _SANDBOX_READY = False
        _SANDBOX_WARN = "Sandbox helper unavailable; falling back to Store-backed FS."
        return False

    try:
        # Verify the sandbox has the required service; ignore returned version
        await tool_support_sandbox(tool_name)
        _SANDBOX_READY = True
        return True
    except Exception as exc:
        _SANDBOX_READY = False
        # Prefer the rich guidance message from PrerequisiteError if present
        _SANDBOX_WARN = str(exc) or ("Sandbox service not available; falling back to Store-backed FS.")
        # Best‑effort structured warning
        try:
            # Local import to avoid circulars at module import time
            from .tools import _log_tool_event

            _log_tool_event(
                name="files:sandbox_preflight",
                phase="warn",
                extra={"ok": False, "warning": _SANDBOX_WARN},
            )
        except Exception:
            pass
        return False


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


def _truthy(env_val: str | None) -> bool:
    """Return True for common truthy string values."""
    if env_val is None:
        return False
    return env_val.strip().lower() in {"1", "true", "yes", "on"}


def _fs_root() -> str:
    """Get filesystem root path for sandbox mode confinement.

    Returns the absolute path that confines sandbox file operations.
    Default is '/repo' if INSPECT_AGENTS_FS_ROOT is not set.
    """
    root = os.getenv("INSPECT_AGENTS_FS_ROOT", "/repo")
    # Ensure it's an absolute path
    if not os.path.isabs(root):
        root = os.path.abspath(root)
    return root


def _max_bytes() -> int:
    """Get maximum file size in bytes from environment.

    Returns the byte ceiling for file operations to prevent OOM and long stalls.
    Default is 5,000,000 bytes (5MB) if INSPECT_AGENTS_FS_MAX_BYTES is not set.
    """
    try:
        return int(os.getenv("INSPECT_AGENTS_FS_MAX_BYTES", "5000000"))
    except ValueError:
        return 5000000


async def _deny_symlink(path: str) -> None:
    """Deny access to symlinks in sandbox mode.

    Args:
        path: The path to check for symlinks

    Raises:
        ToolException: If the path is a symlink or check fails
    """
    # Import here to use the actual ToolException
    try:
        from inspect_tool_support._util.common_types import ToolException as _ToolException
    except ImportError:
        _ToolException = ToolException  # noqa: N806

    try:
        # If sandbox bash support isn't available (e.g., unit tests without a sandbox),
        # skip symlink verification rather than failing the operation.
        if not await _ensure_sandbox_ready("bash session"):
            return

        import shlex

        from inspect_ai.tool._tools._bash_session import bash_session

        bash = bash_session()
        # Properly escape the path for shell execution
        escaped_path = shlex.quote(path)

        with anyio.fail_after(_default_tool_timeout()):
            result = await bash(action="run", command=f"test -L {escaped_path} && echo SYMLINK || echo OK")

        # Check the result
        if result and hasattr(result, "stdout"):
            output = result.stdout.strip() if result.stdout else ""
            if output == "SYMLINK":
                raise _ToolException(
                    f"Access denied: '{path}' is a symbolic link. "
                    f"Symbolic links are not allowed in sandbox mode for security reasons."
                )
            # For any non-SYMLINK output (including empty / unexpected), treat as OK.
            return
        else:
            # No result or no stdout — treat as non-fatal in best-effort mode.
            return

    except _ToolException:
        # Re-raise explicit policy violations (e.g., actual symlink)
        raise
    except Exception:
        # Best-effort only: if the check itself fails (no sandbox, stub signature
        # mismatch, etc.), skip symlink enforcement rather than failing the op.
        return


def _validate_sandbox_path(path: str) -> str:
    """Validate that a path is within the configured FS root for sandbox mode.

    Args:
        path: The path to validate

    Returns:
        The normalized absolute path if valid

    Raises:
        ToolException: If the path is outside the configured root
    """
    # Import here to use the actual ToolException
    try:
        from inspect_tool_support._util.common_types import ToolException as _ToolException
    except ImportError:
        _ToolException = ToolException  # noqa: N806

    # Get the configured root
    root = _fs_root()

    # Normalize the input path to absolute
    if not os.path.isabs(path):
        # For relative paths, join with the root
        abs_path = os.path.join(root, path)
    else:
        abs_path = path

    # Normalize the path (resolve . and .. components)
    normalized_path = os.path.normpath(abs_path)

    # Check if the normalized path starts with the root
    if not normalized_path.startswith(root + os.sep) and normalized_path != root:
        raise _ToolException(
            f"Access denied: path '{path}' is outside the configured filesystem root '{root}'. "
            f"Only paths within the root are allowed in sandbox mode."
        )

    return normalized_path


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
    """Execute ls command.

    Sandbox vs store:
    - Sandbox: proxies via `bash_session` running `ls -1` inside the sandbox.
    - Store: lists files tracked by the in‑memory `Files` store for this instance.

    Notes: falls back from sandbox to store if sandbox is unavailable.
    """
    from inspect_ai.util._store_model import store_as

    # Import lazily to avoid circular import during module import
    from .tools import _log_tool_event

    _t0 = _log_tool_event(
        name="files:ls",
        phase="start",
        args={"instance": params.instance},
    )

    # Sandbox FS mode: use bash_session to run ls command
    if _use_sandbox_fs() and await _ensure_sandbox_ready("bash session"):
        try:
            # Use the configured FS root for ls operation
            root = _fs_root()

            import shlex

            from inspect_ai.tool._tools._bash_session import bash_session

            bash = bash_session()
            # Properly escape the root path for shell execution
            escaped_root = shlex.quote(root)
            with anyio.fail_after(_default_tool_timeout()):
                result = await bash(action="run", command=f"ls -1 {escaped_root}")
                if result and hasattr(result, "stdout") and result.stdout:
                    # Parse output into list, filtering empty lines
                    file_list = [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]
                else:
                    file_list = []

            if _use_typed_results():
                _log_tool_event(
                    name="files:ls",
                    phase="end",
                    extra={"ok": True, "count": len(file_list)},
                    t0=_t0,
                )
                return FileListResult(files=file_list)
            _log_tool_event(
                name="files:ls",
                phase="end",
                extra={"ok": True, "count": len(file_list)},
                t0=_t0,
            )
            return file_list
        except Exception:
            # Graceful fallback to store-backed mode
            pass

    # Store-backed mode (in-memory Files store) with timeout guard
    with anyio.fail_after(_default_tool_timeout()):
        files = store_as(Files, instance=params.instance)
        file_list = files.list_files()

    if _use_typed_results():
        _log_tool_event(
            name="files:ls",
            phase="end",
            extra={"ok": True, "count": len(file_list) if isinstance(file_list, list) else len(file_list.files)},
            t0=_t0,
        )
        return FileListResult(files=file_list)
    _log_tool_event(
        name="files:ls",
        phase="end",
        extra={"ok": True, "count": len(file_list) if isinstance(file_list, list) else len(file_list.files)},
        t0=_t0,
    )
    return file_list


async def execute_read(params: ReadParams) -> str | FileReadResult:
    """Execute read command.

    Sandbox vs store:
    - Sandbox: routes through `text_editor('view')` with `view_range=[start,end]`.
    - Store: reads from the in‑memory `Files` store for this instance.

    Limits: returns at most `limit` lines (default 2000), truncates each line to 2000
    characters, and enforces byte ceiling from INSPECT_AGENTS_FS_MAX_BYTES to prevent OOM.
    Path traversal protection relies on sandbox isolation when in sandbox mode.
    """
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
    if _use_sandbox_fs() and await _ensure_sandbox_ready("editor"):
        # Validate path is within configured root first (before try block to prevent fallback)
        validated_path = _validate_sandbox_path(params.file_path)

        # Deny symlinks for security
        await _deny_symlink(validated_path)

        try:
            # Preflight check: attempt wc -c via bash to enforce byte ceiling.
            # If bash isn't available (common in unit tests), gracefully skip.
            file_bytes: int | None = None
            try:
                import shlex

                from inspect_ai.tool._tools._bash_session import bash_session

                bash = bash_session()
                escaped_path = shlex.quote(validated_path)
                with anyio.fail_after(_default_tool_timeout()):
                    wc_result = await bash(action="run", command=f"wc -c {escaped_path}")
                    if wc_result and hasattr(wc_result, "stdout") and wc_result.stdout:
                        try:
                            file_bytes = int(wc_result.stdout.strip().split()[0])
                        except (ValueError, IndexError):
                            file_bytes = None
            except Exception:
                # Ignore wc failures; proceed to editor read
                file_bytes = None

            if file_bytes is not None:
                max_bytes = _max_bytes()
                if file_bytes > max_bytes:
                    # Import here to use the same ToolException as the tools module
                    try:
                        from inspect_tool_support._util.common_types import ToolException as _ToolException
                    except ImportError:
                        _ToolException = ToolException  # noqa: N806
                    _log_tool_event(
                        name="files:read",
                        phase="error",
                        extra={
                            "ok": False,
                            "error": "FileSizeExceeded",
                            "actual_bytes": file_bytes,
                            "max_bytes": max_bytes,
                        },
                        t0=_t0,
                    )
                    raise _ToolException(
                        f"File exceeds maximum size limit: {file_bytes:,} bytes > {max_bytes:,} bytes. "
                        f"Use a smaller limit parameter or increase INSPECT_AGENTS_FS_MAX_BYTES."
                    )

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
                    path=validated_path,
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

    # Enforce byte ceiling to prevent OOM and long stalls
    content_bytes = len(content.encode("utf-8"))
    max_bytes = _max_bytes()
    if content_bytes > max_bytes:
        try:
            from inspect_tool_support._util.common_types import ToolException as _ToolException
        except ImportError:
            _ToolException = ToolException  # noqa: N806
        _log_tool_event(
            name="files:read",
            phase="error",
            extra={"ok": False, "error": "FileSizeExceeded", "actual_bytes": content_bytes, "max_bytes": max_bytes},
            t0=_t0,
        )
        raise _ToolException(
            f"File exceeds maximum size limit: {content_bytes:,} bytes > {max_bytes:,} bytes. "
            f"Use a smaller limit parameter or increase INSPECT_AGENTS_FS_MAX_BYTES."
        )

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
    """Execute write command.

    Sandbox vs store:
    - Sandbox: routes through `text_editor('create')` to write a file.
    - Store: writes to the in‑memory `Files` store for this instance.

    Limits: enforces byte ceiling from INSPECT_AGENTS_FS_MAX_BYTES to prevent OOM.
    Content is not sanitized; ensure trusted input.
    """
    from inspect_ai.util._store_model import store_as

    from .tools import _log_tool_event

    _t0 = _log_tool_event(
        name="files:write",
        phase="start",
        args={"file_path": params.file_path, "content_len": len(params.content), "instance": params.instance},
    )

    # Read-only guard in sandbox mode
    if _use_sandbox_fs() and _truthy(os.getenv("INSPECT_AGENTS_FS_READ_ONLY")):
        try:
            from inspect_tool_support._util.common_types import ToolException as _ToolException
        except ImportError:
            _ToolException = ToolException  # noqa: N806
        _log_tool_event(name="files:write", phase="error", extra={"ok": False, "error": "SandboxReadOnly"}, t0=_t0)
        raise _ToolException("SandboxReadOnly")

    # Enforce byte ceiling to prevent OOM and long stalls
    content_bytes = len(params.content.encode("utf-8"))
    max_bytes = _max_bytes()
    if content_bytes > max_bytes:
        # Import here to use the same ToolException as the tools module
        try:
            from inspect_tool_support._util.common_types import ToolException as _ToolException
        except ImportError:
            _ToolException = ToolException  # noqa: N806
        _log_tool_event(
            name="files:write",
            phase="error",
            extra={"ok": False, "error": "FileSizeExceeded", "actual_bytes": content_bytes, "max_bytes": max_bytes},
            t0=_t0,
        )
        raise _ToolException(
            f"File content exceeds maximum size limit: {content_bytes:,} bytes > {max_bytes:,} bytes. "
            f"Consider breaking the content into smaller files or increase INSPECT_AGENTS_FS_MAX_BYTES."
        )

    summary = f"Updated file {params.file_path}"

    if _use_sandbox_fs() and await _ensure_sandbox_ready("editor"):
        # Validate path is within configured root first (before try block to prevent fallback)
        validated_path = _validate_sandbox_path(params.file_path)

        # Deny symlinks for security
        await _deny_symlink(validated_path)

        try:
            from inspect_ai.tool._tools._text_editor import text_editor

            editor = text_editor()
            with anyio.fail_after(_default_tool_timeout()):
                await editor(command="create", path=validated_path, file_text=params.content)

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
    """Execute edit command.

    Sandbox vs store:
    - Sandbox: routes through `text_editor('str_replace')`; replacement count is
      not returned by the underlying tool.
    - Store: edits the in‑memory `Files` store and reports replacement count.

    Limits: enforces byte ceiling from INSPECT_AGENTS_FS_MAX_BYTES to prevent OOM.
    String replacement is not validated; ensure trusted input.
    """
    from inspect_ai.util._store_model import store_as

    from .tools import _log_tool_event

    _t0 = _log_tool_event(
        name="files:edit",
        phase="start",
        args={
            "file_path": params.file_path,
            "old_len": len(params.old_string),
            "new_len": len(params.new_string),
            "replace_all": params.replace_all,
            "instance": params.instance,
        },
    )
    # Read-only guard in sandbox mode
    if _use_sandbox_fs() and _truthy(os.getenv("INSPECT_AGENTS_FS_READ_ONLY")):
        try:
            from inspect_tool_support._util.common_types import ToolException as _ToolException
        except ImportError:
            _ToolException = ToolException  # noqa: N806
        _log_tool_event(name="files:edit", phase="error", extra={"ok": False, "error": "SandboxReadOnly"}, t0=_t0)
        raise _ToolException("SandboxReadOnly")
    # For sandbox mode, we need to preflight check file size before edit
    if _use_sandbox_fs() and await _ensure_sandbox_ready("editor"):
        # Validate path is within configured root first (before try block to prevent fallback)
        validated_path = _validate_sandbox_path(params.file_path)

        # Deny symlinks for security
        await _deny_symlink(validated_path)

        try:
            # Preflight check: attempt wc -c via bash to estimate new size. If bash
            # isn't available (common in unit tests), skip estimation.
            current_bytes: int | None = None
            try:
                import shlex

                from inspect_ai.tool._tools._bash_session import bash_session

                bash = bash_session()
                escaped_path = shlex.quote(validated_path)
                with anyio.fail_after(_default_tool_timeout()):
                    wc_result = await bash(action="run", command=f"wc -c {escaped_path}")
                    if wc_result and hasattr(wc_result, "stdout") and wc_result.stdout:
                        try:
                            current_bytes = int(wc_result.stdout.strip().split()[0])
                        except (ValueError, IndexError):
                            current_bytes = None
            except Exception:
                current_bytes = None

            if current_bytes is not None:
                # Estimate new size based on string replacement (approximate)
                old_bytes = len(params.old_string.encode("utf-8"))
                new_bytes = len(params.new_string.encode("utf-8"))
                estimated_new_bytes = current_bytes + (new_bytes - old_bytes)

                max_bytes = _max_bytes()
                if estimated_new_bytes > max_bytes:
                    # Import here to use the same ToolException as the tools module
                    try:
                        from inspect_tool_support._util.common_types import ToolException as _ToolException
                    except ImportError:
                        _ToolException = ToolException  # noqa: N806
                    _log_tool_event(
                        name="files:edit",
                        phase="error",
                        extra={
                            "ok": False,
                            "error": "FileSizeExceeded",
                            "estimated_bytes": estimated_new_bytes,
                            "max_bytes": max_bytes,
                        },
                        t0=_t0,
                    )
                    raise _ToolException(
                        f"Edit would result in file exceeding maximum size limit: ~{estimated_new_bytes:,} bytes > {max_bytes:,} bytes. "
                        f"Consider smaller edits or increase INSPECT_AGENTS_FS_MAX_BYTES."
                    )

            from inspect_ai.tool._tools._text_editor import text_editor

            editor = text_editor()
            with anyio.fail_after(_default_tool_timeout()):
                await editor(
                    command="str_replace",
                    path=validated_path,
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

    # Enforce byte ceiling on the updated content
    updated_bytes = len(updated.encode("utf-8"))
    max_bytes = _max_bytes()
    if updated_bytes > max_bytes:
        try:
            from inspect_tool_support._util.common_types import ToolException as _ToolException
        except ImportError:
            _ToolException = ToolException  # noqa: N806
        _log_tool_event(
            name="files:edit",
            phase="error",
            extra={"ok": False, "error": "FileSizeExceeded", "actual_bytes": updated_bytes, "max_bytes": max_bytes},
            t0=_t0,
        )
        raise _ToolException(
            f"Edit would result in file exceeding maximum size limit: {updated_bytes:,} bytes > {max_bytes:,} bytes. "
            f"Consider smaller edits or increase INSPECT_AGENTS_FS_MAX_BYTES."
        )

    files.put_file(params.file_path, updated)

    summary = f"Updated file {params.file_path}"
    if _use_typed_results():
        _log_tool_event(name="files:edit", phase="end", extra={"ok": True, "replaced": replacement_count}, t0=_t0)
        return FileEditResult(path=params.file_path, replaced=replacement_count, summary=summary)
    _log_tool_event(name="files:edit", phase="end", extra={"ok": True, "replaced": replacement_count}, t0=_t0)
    return summary


async def execute_delete(params: DeleteParams) -> str | FileDeleteResult:
    """Execute delete command.

    Sandbox vs store:
    - Sandbox: delete is disabled to avoid accidental host‑FS deletion.
    - Store: delete is supported against the in‑memory `Files` store.
    """
    from inspect_ai.util._store_model import store_as

    from .tools import _log_tool_event

    _t0 = _log_tool_event(
        name="files:delete",
        phase="start",
        args={"file_path": params.file_path, "instance": params.instance},
    )

    # Sandbox mode: disabled for safety; if read-only flag is set, return specific error
    if _use_sandbox_fs() and _truthy(os.getenv("INSPECT_AGENTS_FS_READ_ONLY")):
        try:
            from inspect_tool_support._util.common_types import ToolException as _ToolException
        except ImportError:
            _ToolException = ToolException  # noqa: N806
        _log_tool_event(name="files:delete", phase="error", extra={"ok": False, "error": "SandboxReadOnly"}, t0=_t0)
        raise _ToolException("SandboxReadOnly")

    # Sandbox mode: disabled for safety
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
        raise _ToolException(
            "delete is disabled in sandbox mode; set INSPECT_AGENTS_FS_MODE=store "
            "to delete from the in-memory Files store"
        )

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

    Supports commands: ls, read, write, edit, delete.

    Sandbox vs store:
    - Sandbox (INSPECT_AGENTS_FS_MODE=sandbox): routes reads/writes/edits via
      Inspect's `text_editor` tool and proxies `ls` via `bash_session`, isolating
      operations from the host filesystem. Delete is disabled in sandbox mode.
    - Store (default): operates on an in‑memory virtual filesystem (`Files`) that
      is isolated per execution context.

    Limits: reads return at most `limit` lines (default 2000) and each line is
    truncated to 2000 characters to bound output size.

    Security: paths are not validated for traversal; rely on sandbox isolation
    when handling untrusted input.
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
            description=(
                "Unified file operations tool (ls, read, write, edit, delete). Delete disabled in sandbox mode."
            ),
            parameters=params,
        ).as_tool()

    return _factory()

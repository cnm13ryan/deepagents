from __future__ import annotations

"""Inspect‑native tools for the deepagents rewrite.

Currently includes:
- write_todos: update the shared Todos list in the Store
"""

from typing import TYPE_CHECKING, List
import os
import anyio

# Avoid importing inspect_ai.tool at module import time; tests stub package
if TYPE_CHECKING:  # pragma: no cover - only for type checkers
    from inspect_ai.tool._tool import Tool  # noqa: F401
    from inspect_ai.tool._tool_def import ToolDef  # noqa: F401
    from inspect_ai.tool._tool_params import ToolParams  # noqa: F401
    from inspect_ai.util._json import json_schema  # noqa: F401
    from inspect_ai.util._store_model import store_as  # noqa: F401

from .state import Todo, Todos


def _fs_mode() -> str:
    """Return filesystem mode: 'store' (default) or 'sandbox'.

    Controlled by env var `INSPECT_AGENTS_FS_MODE`. Any value other than
    'sandbox' uses the default in-memory Store. Sandbox mode writes to the
    host fs via Inspect's text_editor tool; ensure a safe sandbox.
    """
    return os.getenv("INSPECT_AGENTS_FS_MODE", "store").strip().lower()


def _use_sandbox_fs() -> bool:
    return _fs_mode() == "sandbox"


def _default_tool_timeout() -> float:
    try:
        return float(os.getenv("INSPECT_AGENTS_TOOL_TIMEOUT", "15"))
    except Exception:
        return 15.0


def _truthy(env_val: str | None) -> bool:
    if env_val is None:
        return False
    return env_val.strip().lower() in {"1", "true", "yes", "on"}


def standard_tools() -> list[object]:
    """Return a list of standard Inspect‑AI tools.

    Controlled by environment flags to keep defaults safe:

    - INSPECT_ENABLE_THINK: enable `think()` (default: true)
    - INSPECT_ENABLE_WEB_SEARCH: enable `web_search(...)` when a provider is available
      (default: auto if Tavily or Google keys are set)
    - INSPECT_ENABLE_EXEC: enable `bash()` and `python()` (default: false)
    - INSPECT_ENABLE_WEB_BROWSER: enable `web_browser(...)` tools (default: false)
    - INSPECT_ENABLE_TEXT_EDITOR_TOOL: expose `text_editor()` as a tool (default: false)

    Notes:
    - Our file tools (read_file/write_file/edit_file/ls) already use `text_editor`
      internally when `INSPECT_AGENTS_FS_MODE=sandbox`; exposing `text_editor()`
      directly is optional and disabled by default.
    - Web search providers are auto‑configured using environment variables:
      Tavily (TAVILY_API_KEY) or Google CSE (GOOGLE_CSE_ID/GOOGLE_CSE_API_KEY).
    """
    tools: list[object] = []

    # Local imports to avoid heavy imports at module import time
    try:
        from inspect_ai.tool import think, web_search
        from inspect_ai.tool._tools._execute import bash, python as py_exec
        from inspect_ai.tool._tools._text_editor import text_editor
        from inspect_ai.tool._tools._web_browser import web_browser
    except Exception:
        # If inspect_ai is stubbed in tests, just return empty; callers can still use our built‑ins
        return tools

    # think()
    if not os.getenv("INSPECT_ENABLE_THINK") or _truthy(os.getenv("INSPECT_ENABLE_THINK", "1")):
        try:
            tools.append(think())
        except Exception:
            pass

    # web_search(...)
    enable_web_search_env = os.getenv("INSPECT_ENABLE_WEB_SEARCH")
    enable_web_search = (
        _truthy(enable_web_search_env)
        if enable_web_search_env is not None
        else (os.getenv("TAVILY_API_KEY") or (os.getenv("GOOGLE_CSE_ID") and os.getenv("GOOGLE_CSE_API_KEY"))) is not None
    )
    if enable_web_search:
        try:
            providers_cfg: list[object] = []
            # Prefer internal provider if user explicitly requests via INSPECT_WEB_SEARCH_INTERNAL
            internal = (os.getenv("INSPECT_WEB_SEARCH_INTERNAL") or "").strip().lower()
            if internal in {"openai", "anthropic", "perplexity", "gemini", "grok"}:
                providers_cfg.append(internal)

            # Add external providers based on available credentials
            if os.getenv("TAVILY_API_KEY"):
                providers_cfg.append({"tavily": True})
            if os.getenv("GOOGLE_CSE_ID") and os.getenv("GOOGLE_CSE_API_KEY"):
                providers_cfg.append({"google": True})

            providers = providers_cfg or None
            tools.append(web_search(providers))
        except Exception:
            # If provider configuration is invalid or missing, skip silently
            pass

    # bash() and python() (disabled by default)
    if _truthy(os.getenv("INSPECT_ENABLE_EXEC")):
        try:
            tools.extend([bash(), py_exec()])
        except Exception:
            pass

    # web_browser (disabled by default; heavy)
    if _truthy(os.getenv("INSPECT_ENABLE_WEB_BROWSER")):
        try:
            tools.extend(web_browser())
        except Exception:
            pass

    # text_editor (disabled by default; only meaningful with sandbox FS)
    if _truthy(os.getenv("INSPECT_ENABLE_TEXT_EDITOR_TOOL")) and _use_sandbox_fs():
        try:
            tools.append(text_editor())
        except Exception:
            pass

    return tools


def write_todos():  # -> Tool
    """Update the shared todo list.

    Accepts a list of todos and writes them to the shared Todos model in the
    current Inspect Store, returning a human-readable confirmation string.
    """

    # Local imports to avoid executing inspect_ai.tool __init__ during module import
    from inspect_ai.tool._tool import Tool, tool
    from inspect_ai.tool._tool_def import ToolDef
    from inspect_ai.tool._tool_params import ToolParams
    from inspect_ai.util._json import json_schema
    from inspect_ai.util._store_model import store_as

    @tool
    def _factory() -> Tool:
        async def execute(todos: list[Todo]) -> str:
            model = store_as(Todos)
            model.set_todos(todos)
            rendered = [
                t.model_dump() if hasattr(t, "model_dump") else t for t in model.todos
            ]
            return f"Updated todo list to {rendered}"

        params = ToolParams()
        params.properties["todos"] = json_schema(list[Todo])  # type: ignore[arg-type]
        params.properties["todos"].description = "List of todo items to write"
        params.required.append("todos")

        return ToolDef(
            execute,
            name="write_todos",
            description="Update the shared todo list.",
            parameters=params,
        ).as_tool()

    return _factory()


def ls():  # -> Tool
    """List all files in the Files store.

    Optionally scope to a Files(instance=...) for per-agent isolation.
    """
    from inspect_ai.tool._tool import Tool, tool
    from inspect_ai.tool._tool_def import ToolDef
    from inspect_ai.tool._tool_params import ToolParams
    from inspect_ai.util._json import json_schema
    from inspect_ai.util._store_model import store_as
    from .state import Files

    @tool
    def _factory() -> Tool:
        async def execute(instance: str | None = None) -> list[str]:
            files = store_as(Files, instance=instance)
            return files.list_files()

        params = ToolParams()
        params.properties["instance"] = json_schema(str)
        params.properties["instance"].description = "Optional Files instance for isolation"
        # instance optional

        return ToolDef(
            execute,
            name="ls",
            description="List all files in the virtual store.",
            parameters=params,
        ).as_tool()

    return _factory()


def read_file():  # -> Tool
    """Read a file with cat -n formatting and safety limits.

    Mirrors deepagents semantics: offset/limit by lines, per-line 2000-char truncation,
    and friendly error messages.
    """
    from inspect_ai.tool._tool import Tool, tool
    from inspect_ai.tool._tool_def import ToolDef
    from inspect_ai.tool._tool_params import ToolParams
    from inspect_ai.util._json import json_schema
    from inspect_ai.util._store_model import store_as
    from .state import Files

    @tool
    def _factory() -> Tool:
        async def execute(
            file_path: str,
            offset: int = 0,
            limit: int = 2000,
            instance: str | None = None,
        ) -> str:
            # Sandbox FS mode: call text_editor('view', ...) then format lines
            if _use_sandbox_fs():
                try:
                    from inspect_ai.tool._tools._text_editor import text_editor
                    editor = text_editor()
                    start_line = max(1, int(offset) + 1)
                    if limit is None or limit <= 0:
                        view_range = [start_line, -1]
                    else:
                        view_range = [start_line, start_line + int(limit) - 1]
                    raw = await editor(
                        command="view",
                        path=file_path,
                        view_range=view_range,
                    )
                    # Format numbered/truncated lines to preserve semantics
                    if raw is None or str(raw).strip() == "":
                        return "System reminder: File exists but has empty contents"
                    lines = str(raw).splitlines()
                    out_lines: list[str] = []
                    ln = start_line
                    for line_content in lines:
                        if len(line_content) > 2000:
                            line_content = line_content[:2000]
                        out_lines.append(f"{ln:6d}\t{line_content}")
                        ln += 1
                    return "\n".join(out_lines)
                except Exception:
                    # Graceful fallback to store-backed mode
                    pass

            # Store-backed with timeout guard
            with anyio.fail_after(_default_tool_timeout()):
                files = store_as(Files, instance=instance)
                content = files.get_file(file_path)
            if content is None:
                return f"Error: File '{file_path}' not found"

            if not content or content.strip() == "":
                return "System reminder: File exists but has empty contents"

            lines = content.splitlines()
            start_idx = offset
            end_idx = min(start_idx + limit, len(lines))

            if start_idx >= len(lines):
                return f"Error: Line offset {offset} exceeds file length ({len(lines)} lines)"

            out_lines: list[str] = []
            for i in range(start_idx, end_idx):
                line_content = lines[i]
                if len(line_content) > 2000:
                    line_content = line_content[:2000]
                line_number = i + 1
                out_lines.append(f"{line_number:6d}\t{line_content}")

            return "\n".join(out_lines)

        params = ToolParams()
        params.properties["file_path"] = json_schema(str)
        params.properties["file_path"].description = "Path to read"
        params.properties["offset"] = json_schema(int)
        params.properties["offset"].description = "Line offset (0-based)"
        params.properties["offset"].default = 0
        params.properties["limit"] = json_schema(int)
        params.properties["limit"].description = "Max lines to return"
        params.properties["limit"].default = 2000
        params.properties["instance"] = json_schema(str)
        params.properties["instance"].description = "Optional Files instance for isolation"
        params.required.append("file_path")

        return ToolDef(
            execute,
            name="read_file",
            description="Read a file with numbered lines and truncation.",
            parameters=params,
        ).as_tool()

    return _factory()


def write_file():  # -> Tool
    """Write content to a file in the Files store."""
    from inspect_ai.tool._tool import Tool, tool
    from inspect_ai.tool._tool_def import ToolDef
    from inspect_ai.tool._tool_params import ToolParams
    from inspect_ai.util._json import json_schema
    from inspect_ai.util._store_model import store_as
    from .state import Files

    @tool
    def _factory() -> Tool:
        async def execute(
            file_path: str,
            content: str,
            instance: str | None = None,
        ) -> str:
            if _use_sandbox_fs():
                try:
                    from inspect_ai.tool._tools._text_editor import text_editor
                    editor = text_editor()
                    await editor(command="create", path=file_path, file_text=content)
                    return f"Updated file {file_path}"
                except Exception:
                    pass
            # Store-backed with timeout guard
            with anyio.fail_after(_default_tool_timeout()):
                files = store_as(Files, instance=instance)
                files.put_file(file_path, content)
            return f"Updated file {file_path}"

        params = ToolParams()
        params.properties["file_path"] = json_schema(str)
        params.properties["file_path"].description = "Path to write"
        params.properties["content"] = json_schema(str)
        params.properties["content"].description = "Content to write"
        params.properties["instance"] = json_schema(str)
        params.properties["instance"].description = "Optional Files instance for isolation"
        params.required.extend(["file_path", "content"])

        return ToolDef(
            execute,
            name="write_file",
            description="Write file content to the virtual store.",
            parameters=params,
        ).as_tool()

    return _factory()


def edit_file():  # -> Tool
    """Edit a file by replacing a string (first or all occurrences)."""
    from inspect_ai.tool._tool import Tool, tool
    from inspect_ai.tool._tool_def import ToolDef
    from inspect_ai.tool._tool_params import ToolParams
    from inspect_ai.util._json import json_schema
    from inspect_ai.util._store_model import store_as
    from .state import Files

    @tool
    def _factory() -> Tool:
        async def execute(
            file_path: str,
            old_string: str,
            new_string: str,
            replace_all: bool = False,
            instance: str | None = None,
        ) -> str:
            if _use_sandbox_fs():
                try:
                    from inspect_ai.tool._tools._text_editor import text_editor
                    editor = text_editor()
                    await editor(
                        command="str_replace",
                        path=file_path,
                        old_str=old_string,
                        new_str=new_string,
                    )
                    return f"Updated file {file_path}"
                except Exception:
                    pass
            # Store-backed with timeout guard
            with anyio.fail_after(_default_tool_timeout()):
                files = store_as(Files, instance=instance)
                content = files.get_file(file_path)
            if content is None:
                return f"Error: File '{file_path}' not found"

            if old_string not in content:
                return f"Error: String not found in file: '{old_string}'"

            if replace_all:
                updated = content.replace(old_string, new_string)
            else:
                updated = content.replace(old_string, new_string, 1)

            files.put_file(file_path, updated)
            return f"Updated file {file_path}"

        params = ToolParams()
        params.properties["file_path"] = json_schema(str)
        params.properties["file_path"].description = "Path to edit"
        params.properties["old_string"] = json_schema(str)
        params.properties["old_string"].description = "String to replace"
        params.properties["new_string"] = json_schema(str)
        params.properties["new_string"].description = "Replacement string"
        params.properties["replace_all"] = json_schema(bool)
        params.properties["replace_all"].description = "Replace all occurrences if true"
        params.properties["replace_all"].default = False
        params.properties["instance"] = json_schema(str)
        params.properties["instance"].description = "Optional Files instance for isolation"
        params.required.extend(["file_path", "old_string", "new_string"])

        return ToolDef(
            execute,
            name="edit_file",
            description="Edit a file by replacing text.",
            parameters=params,
        ).as_tool()

    return _factory()

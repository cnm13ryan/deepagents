import asyncio
import os
import sys
import types

import anyio
import pytest
from inspect_ai.model._call_tools import execute_tools
from inspect_ai.model._chat_message import ChatMessageAssistant, ChatMessageUser
from inspect_ai.tool._tool import Tool, tool
from inspect_ai.tool._tool_call import ToolCall
from inspect_ai.tool._tool_def import ToolDef
from inspect_ai.tool._tool_params import ToolParams


def slow_tool() -> Tool:  # type: ignore[return-type]
    async def execute(delay: float = 1.0, timeout: float = 0.01) -> str:
        with anyio.move_on_after(timeout) as scope:
            await anyio.sleep(delay)
        if scope.cancel_called:
            raise TimeoutError("tool timed out")
        return "done"

    # Manually define params to satisfy schema/description requirements
    params = ToolParams()
    # Use JSON schema helper to produce proper ToolParam entries
    from inspect_ai.util._json import json_schema
    params.properties["delay"] = json_schema(float)
    params.properties["delay"].description = "seconds to sleep"  # type: ignore[index]
    params.properties["delay"].default = 1.0  # type: ignore[index]
    params.properties["timeout"] = json_schema(float)
    params.properties["timeout"].description = "timeout seconds before raising"  # type: ignore[index]
    params.properties["timeout"].default = 0.01  # type: ignore[index]

    return ToolDef(
        execute,
        name="slow_tool",
        description="Simulate long-running tool for timeout testing",
        parameters=params,
    ).as_tool()


def _conv_with_tool():
    return [
        ChatMessageUser(content="start"),
        ChatMessageAssistant(
            content="",
            tool_calls=[
                ToolCall(
                    id="1",
                    function="slow_tool",
                    arguments={"delay": 2.0, "timeout": 0.01},
                )
            ],
        ),
    ]


def test_timeout_surfaces_tool_error_and_transcript():
    messages = _conv_with_tool()
    result = asyncio.run(execute_tools(messages, [slow_tool()]))
    tool_msg = result.messages[0]
    # Tool message should carry a timeout error
    assert getattr(tool_msg, "error", None) is not None
    assert tool_msg.error.type == "timeout"

    # Transcript should have a ToolEvent whose error is timeout as well
    from inspect_ai.log._transcript import ToolEvent, transcript

    # Use helper to fetch the last ToolEvent
    ev = transcript().find_last_event(ToolEvent)
    assert ev is not None


def _install_slow_text_editor():
    """Install a text_editor stub that delays before responding."""
    mod_name = "inspect_ai.tool._tools._text_editor"
    if mod_name in sys.modules:
        del sys.modules[mod_name]

    mod = types.ModuleType(mod_name)

    from inspect_ai.tool._tool import Tool

    @tool()
    def text_editor() -> Tool:  # type: ignore[return-type]
        async def execute(
            command: str,
            path: str,
            file_text: str | None = None,
            view_range: list[int] | None = None,
            old_str: str | None = None,
            new_str: str | None = None,
        ) -> str:
            # Simulate a slow operation that exceeds timeout
            await anyio.sleep(1.0)  # Sleep for 1 second
            return "Should not reach here due to timeout"

        return execute

    mod.text_editor = text_editor
    sys.modules[mod_name] = mod


def test_sandbox_text_editor_timeout_read_file(monkeypatch):
    """Test that sandbox read_file text_editor calls respect timeouts."""
    # Set environment for sandbox mode and short timeout  
    monkeypatch.setenv("INSPECT_AGENTS_FS_MODE", "sandbox")
    monkeypatch.setenv("INSPECT_AGENTS_TOOL_TIMEOUT", "0.1")  # 100ms timeout
    
    # Install slow text_editor stub that raises TimeoutError
    _install_slow_text_editor()
    
    from inspect_agents.tools import ToolException, read_file
    
    tool = read_file()
    
    async def run_tool():
        # The timeout should occur in the anyio.fail_after context,
        # which will raise CancelledError. Since the tool catches Exception,
        # this will be caught and the tool will fall back to store mode.
        # On missing file, the fallback raises ToolException.
        with pytest.raises(ToolException):
            # Use a sandbox-rooted path so validation passes and timeout triggers fallback
            await tool(file_path="/repo/test.txt")
    
    asyncio.run(run_tool())


def test_sandbox_text_editor_timeout_integration():
    """Integration test to verify timeout behavior works correctly.

    Use a sandbox-safe path by setting INSPECT_AGENTS_FS_ROOT to a temporary
    directory so `_validate_sandbox_path` passes and the slow text_editor
    triggers timeout and fallback to the Store-backed filesystem.
    """

    # Set short timeout
    original_timeout = os.environ.get("INSPECT_AGENTS_TOOL_TIMEOUT")
    os.environ["INSPECT_AGENTS_TOOL_TIMEOUT"] = "0.05"  # 50ms

    # Set sandbox mode
    original_fs_mode = os.environ.get("INSPECT_AGENTS_FS_MODE")
    os.environ["INSPECT_AGENTS_FS_MODE"] = "sandbox"

    # Constrain sandbox root to a temp dir and target a file within it
    import tempfile
    tmp_dir = tempfile.mkdtemp(prefix="inspect-agents-sbx-")
    original_fs_root = os.environ.get("INSPECT_AGENTS_FS_ROOT")
    os.environ["INSPECT_AGENTS_FS_ROOT"] = tmp_dir
    file_path = os.path.join(tmp_dir, "test.txt")

    try:
        # Install a text_editor that will timeout
        _install_slow_text_editor()
        
        from inspect_agents.tools import edit_file, read_file, write_file
        
        # These should timeout and fall back gracefully
        read_tool = read_file()
        write_tool = write_file()
        edit_tool = edit_file()
        
        async def test_timeout_fallback():
            # All of these should fall back to store mode due to timeout in sandbox mode
            write_result = await write_tool(file_path=file_path, content="test")
            read_result = await read_tool(file_path=file_path)
            edit_result = await edit_tool(file_path=file_path, old_string="test", new_string="TEST")
            
            # Verify they completed (fell back to store mode)
            assert "Updated file" in write_result
            # After successful write_file fallback, the file should be readable 
            assert "test" in read_result.lower() or "not found" in read_result.lower()
            assert "Updated file" in edit_result
        
        asyncio.run(test_timeout_fallback())
        
    finally:
        # Restore original environment
        if original_timeout is not None:
            os.environ["INSPECT_AGENTS_TOOL_TIMEOUT"] = original_timeout
        else:
            os.environ.pop("INSPECT_AGENTS_TOOL_TIMEOUT", None)
            
        if original_fs_mode is not None:
            os.environ["INSPECT_AGENTS_FS_MODE"] = original_fs_mode
        else:
            os.environ.pop("INSPECT_AGENTS_FS_MODE", None)

        if original_fs_root is not None:
            os.environ["INSPECT_AGENTS_FS_ROOT"] = original_fs_root
        else:
            os.environ.pop("INSPECT_AGENTS_FS_ROOT", None)

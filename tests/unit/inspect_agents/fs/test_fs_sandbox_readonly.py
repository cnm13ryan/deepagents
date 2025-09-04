import asyncio
import json
import logging
import os
from unittest.mock import patch

import pytest

from inspect_agents.tools import ToolException as ToolExceptionTools
from inspect_agents.tools import delete_file, edit_file, write_file
from inspect_agents.tools_files import ToolException as ToolExceptionFiles


def _collect_tool_events(caplog):
    events = []
    for rec in caplog.records:
        msg = rec.getMessage()
        if isinstance(msg, str) and msg.startswith("tool_event "):
            try:
                payload = json.loads(msg[len("tool_event ") :])
                events.append(payload)
            except Exception:
                pass
    return events


def test_write_sandbox_readonly_raises_and_logs(caplog):
    caplog.set_level(logging.INFO, logger="inspect_agents")
    wf = write_file()

    async def _run():
        with patch.dict(os.environ, {"INSPECT_AGENTS_FS_MODE": "sandbox", "INSPECT_AGENTS_FS_READ_ONLY": "1"}):
            with pytest.raises((ToolExceptionTools, ToolExceptionFiles)) as exc_info:
                await wf(file_path="ro.txt", content="blocked")
            return str(exc_info.value)

    msg = asyncio.run(_run())
    assert "SandboxReadOnly" in msg

    events = _collect_tool_events(caplog)
    err = next((e for e in events if e.get("tool") == "files:write" and e.get("phase") == "error"), None)
    assert err is not None
    assert err.get("error") == "SandboxReadOnly"


def test_edit_sandbox_readonly_raises_and_logs(caplog):
    caplog.set_level(logging.INFO, logger="inspect_agents")
    ef = edit_file()

    async def _run():
        with patch.dict(os.environ, {"INSPECT_AGENTS_FS_MODE": "sandbox", "INSPECT_AGENTS_FS_READ_ONLY": "1"}):
            with pytest.raises((ToolExceptionTools, ToolExceptionFiles)) as exc_info:
                await ef(file_path="ro.txt", old_string="a", new_string="b", replace_all=True)
            return str(exc_info.value)

    msg = asyncio.run(_run())
    assert "SandboxReadOnly" in msg

    events = _collect_tool_events(caplog)
    err = next((e for e in events if e.get("tool") == "files:edit" and e.get("phase") == "error"), None)
    assert err is not None
    assert err.get("error") == "SandboxReadOnly"


def test_delete_sandbox_readonly_raises_and_logs(caplog):
    caplog.set_level(logging.INFO, logger="inspect_agents")
    df = delete_file()

    async def _run():
        with patch.dict(os.environ, {"INSPECT_AGENTS_FS_MODE": "sandbox", "INSPECT_AGENTS_FS_READ_ONLY": "1"}):
            with pytest.raises((ToolExceptionTools, ToolExceptionFiles)) as exc_info:
                await df(file_path="ro.txt")
            return str(exc_info.value)

    msg = asyncio.run(_run())
    assert "SandboxReadOnly" in msg

    events = _collect_tool_events(caplog)
    err = next((e for e in events if e.get("tool") == "files:delete" and e.get("phase") == "error"), None)
    assert err is not None
    assert err.get("error") == "SandboxReadOnly"


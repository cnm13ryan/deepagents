import asyncio
import logging
import sys
import types

import pytest


def test_preflight_skip_returns_false_no_log(monkeypatch, caplog):
    from inspect_agents.tools_files import _ensure_sandbox_ready, reset_sandbox_preflight_cache

    # Ensure no tool stubs short-circuit the check
    sys.modules.pop("inspect_ai.tool._tools._text_editor", None)
    sys.modules.pop("inspect_ai.tool._tools._bash_session", None)

    reset_sandbox_preflight_cache()
    monkeypatch.setenv("INSPECT_SANDBOX_PREFLIGHT", "skip")
    monkeypatch.delenv("INSPECT_SANDBOX_LOG_PATHS", raising=False)

    caplog.set_level(logging.INFO, logger="inspect_agents")

    async def run():
        ready = await _ensure_sandbox_ready("editor")
        assert ready is False

    asyncio.run(run())

    # No sandbox preflight warning should be emitted in skip mode
    for rec in caplog.records:
        msg = rec.getMessage()
        assert "files:sandbox_preflight" not in msg


def test_preflight_force_raises_on_failure(monkeypatch):
    from inspect_agents.tools_files import _ensure_sandbox_ready, reset_sandbox_preflight_cache

    # Ensure import path triggers failure of helper import
    sys.modules.pop("inspect_ai.tool._tools._text_editor", None)
    sys.modules.pop("inspect_ai.tool._tools._bash_session", None)
    sys.modules.pop("inspect_ai.tool._tool_support_helpers", None)

    reset_sandbox_preflight_cache()
    monkeypatch.setenv("INSPECT_SANDBOX_PREFLIGHT", "force")

    async def run():
        with pytest.raises(Exception) as exc:
            await _ensure_sandbox_ready("editor")
        return str(exc.value)

    msg = asyncio.run(run())
    assert "sandbox" in msg.lower()


def test_preflight_ttl_expiry_and_reset(monkeypatch):
    from inspect_agents.tools_files import _ensure_sandbox_ready, reset_sandbox_preflight_cache

    # Provide a stub for tool_support_sandbox to track calls
    mod_name = "inspect_ai.tool._tool_support_helpers"
    sys.modules.pop(mod_name, None)
    calls: list[str] = []
    mod = types.ModuleType(mod_name)

    async def tool_support_sandbox(tool_name: str):  # type: ignore[no-redef]
        calls.append(tool_name)
        return "v1"

    mod.tool_support_sandbox = tool_support_sandbox  # type: ignore[attr-defined]
    sys.modules[mod_name] = mod

    # Ensure no editor/bash stubs short-circuit
    sys.modules.pop("inspect_ai.tool._tools._text_editor", None)
    sys.modules.pop("inspect_ai.tool._tools._bash_session", None)

    reset_sandbox_preflight_cache()
    monkeypatch.setenv("INSPECT_SANDBOX_PREFLIGHT", "auto")
    monkeypatch.setenv("INSPECT_SANDBOX_PREFLIGHT_TTL_SEC", "0.1")

    # First call performs preflight
    async def run1():
        return await _ensure_sandbox_ready("editor")

    assert asyncio.run(run1()) is True
    assert calls == ["editor"]

    # Within TTL → cached
    assert asyncio.run(run1()) is True
    assert calls == ["editor"]  # still one call

    # After TTL → recheck
    asyncio.run(asyncio.sleep(0.12))
    assert asyncio.run(run1()) is True
    assert calls == ["editor", "editor"]

    # Reset API forces next call to re-evaluate immediately
    reset_sandbox_preflight_cache()
    assert asyncio.run(run1()) is True
    assert calls == ["editor", "editor", "editor"]


def test_preflight_logs_context_when_enabled(monkeypatch, caplog):
    from inspect_agents.tools_files import _ensure_sandbox_ready, reset_sandbox_preflight_cache

    # Stub helper to raise and trigger logging path
    mod_name = "inspect_ai.tool._tool_support_helpers"
    sys.modules.pop(mod_name, None)
    mod = types.ModuleType(mod_name)

    async def tool_support_sandbox(tool_name: str):  # type: ignore[no-redef]
        raise RuntimeError("service missing")

    mod.tool_support_sandbox = tool_support_sandbox  # type: ignore[attr-defined]
    sys.modules[mod_name] = mod

    # Ensure no editor/bash stubs short-circuit
    sys.modules.pop("inspect_ai.tool._tools._text_editor", None)
    sys.modules.pop("inspect_ai.tool._tools._bash_session", None)

    reset_sandbox_preflight_cache()
    monkeypatch.setenv("INSPECT_SANDBOX_PREFLIGHT", "auto")
    monkeypatch.setenv("INSPECT_SANDBOX_LOG_PATHS", "1")
    monkeypatch.setenv("INSPECT_AGENTS_FS_ROOT", "/repo")

    caplog.set_level(logging.INFO, logger="inspect_agents")

    async def run():
        return await _ensure_sandbox_ready("editor")

    ready = asyncio.run(run())
    assert ready is False

    # Extract tool_event records and find the sandbox preflight warn
    events = []
    for rec in caplog.records:
        msg = rec.getMessage()
        if isinstance(msg, str) and msg.startswith("tool_event "):
            events.append(msg)

    joined = "\n".join(events)
    assert "\"tool\": \"files:sandbox_preflight\"" in joined
    assert "\"ok\": false" in joined or "\"ok\": False" in joined
    assert "\"fs_root\": \"/repo\"" in joined
    assert "\"sandbox_tool\": \"editor\"" in joined  # context field

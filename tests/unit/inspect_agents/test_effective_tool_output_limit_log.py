import json
import logging

import pytest


@pytest.mark.asyncio
async def test_effective_limit_log_with_env(caplog, monkeypatch):
    # Ensure fresh state for one-time logger and active config
    import inspect_agents.tools as tmod
    from inspect_ai.model._generate_config import GenerateConfig, set_active_generate_config

    monkeypatch.setattr(tmod, "_EFFECTIVE_LIMIT_LOGGED", False, raising=False)
    set_active_generate_config(GenerateConfig())

    # Apply env override
    monkeypatch.setenv("INSPECT_MAX_TOOL_OUTPUT", "8192")

    # Capture logs from our package
    caplog.set_level(logging.INFO, logger="inspect_agents")
    caplog.set_level(logging.INFO, logger="inspect_agents.tools")

    # Trigger the first tool event twice (should log observability once)
    from inspect_agents.tools_files import WriteParams, execute_write

    await execute_write(WriteParams(command="write", file_path="obs_env.txt", content="x"))
    await execute_write(WriteParams(command="write", file_path="obs_env2.txt", content="y"))

    # Extract tool_event payloads
    events = []
    for rec in caplog.records:
        msg = rec.getMessage()
        if isinstance(msg, str) and msg.startswith("tool_event "):
            try:
                payload = json.loads(msg[len("tool_event ") :])
                events.append(payload)
            except Exception:
                pass

    obs = [e for e in events if e.get("tool") == "observability" and e.get("phase") == "info"]
    assert len(obs) == 1
    assert obs[0].get("effective_tool_output_limit") == 8192
    assert obs[0].get("source") == "env"


@pytest.mark.asyncio
async def test_effective_limit_log_default_when_no_env(caplog, monkeypatch):
    # Ensure fresh state for one-time logger and active config
    import inspect_agents.tools as tmod
    from inspect_ai.model._generate_config import (
        GenerateConfig,
        active_generate_config,
        set_active_generate_config,
    )

    monkeypatch.setattr(tmod, "_EFFECTIVE_LIMIT_LOGGED", False, raising=False)
    set_active_generate_config(GenerateConfig())

    # Ensure env is unset
    monkeypatch.delenv("INSPECT_MAX_TOOL_OUTPUT", raising=False)

    # Capture logs
    caplog.set_level(logging.INFO, logger="inspect_agents")
    caplog.set_level(logging.INFO, logger="inspect_agents.tools")

    # Trigger a tool event
    from inspect_agents.tools_files import WriteParams, execute_write

    await execute_write(WriteParams(command="write", file_path="obs_default.txt", content="z"))

    # Extract tool_event payloads
    events = []
    for rec in caplog.records:
        msg = rec.getMessage()
        if isinstance(msg, str) and msg.startswith("tool_event "):
            try:
                payload = json.loads(msg[len("tool_event ") :])
                events.append(payload)
            except Exception:
                pass

    obs = [e for e in events if e.get("tool") == "observability" and e.get("phase") == "info"]
    assert len(obs) == 1

    # Compute expected effective limit following our precedence logic
    cfg_limit = active_generate_config().max_tool_output
    expected = cfg_limit if cfg_limit is not None else 16 * 1024

    assert obs[0].get("effective_tool_output_limit") == expected
    assert obs[0].get("source") == "default"


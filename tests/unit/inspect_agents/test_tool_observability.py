import logging
import json
import pytest

from inspect_agents.tools_files import WriteParams, execute_write


@pytest.mark.asyncio
async def test_files_write_logs_redacted(caplog):
    # Capture INFO level logs from our package
    caplog.set_level(logging.INFO, logger="inspect_agents")

    secret = "MY_TOP_SECRET_TOKEN_12345"
    params = WriteParams(command="write", file_path="obs.txt", content=secret)

    # Execute and capture logs
    await execute_write(params)

    # Extract tool_event records and parse JSON payloads
    events = []
    for rec in caplog.records:
        if isinstance(rec.msg, str) and rec.msg.startswith("tool_event "):
            try:
                payload = json.loads(rec.msg[len("tool_event "):])
                events.append(payload)
            except Exception:
                pass

    # Expect at least a start and end event
    phases = [e.get("phase") for e in events]
    assert "start" in phases and "end" in phases

    # Ensure redaction occurred: secret must not appear; [REDACTED] should
    joined = json.dumps(events)
    assert "[REDACTED]" in joined
    assert secret not in joined

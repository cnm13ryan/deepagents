import json
import logging

import pytest

from inspect_agents.tools_files import EditParams, ReadParams, WriteParams, execute_edit, execute_read, execute_write


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
        msg = rec.getMessage()
        if isinstance(msg, str) and msg.startswith("tool_event "):
            try:
                payload = json.loads(msg[len("tool_event ") :])
                events.append(payload)
            except Exception:
                pass

    # Expect at least a start and end event
    phases = [e.get("phase") for e in events]
    assert "start" in phases and "end" in phases

    # With our new content_len approach, the secret should not appear at all
    # since we don't log the actual content anymore
    joined = json.dumps(events)
    assert secret not in joined

    # Verify that content_len is logged instead of content
    start_events = [e for e in events if e.get("phase") == "start"]
    assert len(start_events) >= 1
    start_args = start_events[0].get("args", {})
    assert "content_len" in start_args
    assert "content" not in start_args


@pytest.mark.asyncio
async def test_files_write_logs_content_length_not_content(caplog):
    """Test that write operation logs content_len instead of content."""
    caplog.set_level(logging.INFO, logger="inspect_agents")

    content = "This is some content that should not appear in logs"
    params = WriteParams(command="write", file_path="test.txt", content=content)

    await execute_write(params)

    # Extract tool_event records
    events = []
    for rec in caplog.records:
        msg = rec.getMessage()
        if isinstance(msg, str) and msg.startswith("tool_event "):
            try:
                payload = json.loads(msg[len("tool_event ") :])
                events.append(payload)
            except Exception:
                pass

    # Find start event
    start_events = [e for e in events if e.get("phase") == "start" and e.get("tool") == "files:write"]
    assert len(start_events) == 1

    start_event = start_events[0]
    args = start_event.get("args", {})

    # Verify content_len is present and content is not
    assert "content_len" in args
    assert args["content_len"] == len(content)
    assert "content" not in args

    # Ensure original content doesn't leak into logs
    joined = json.dumps(events)
    assert content not in joined


@pytest.mark.asyncio
async def test_files_edit_logs_string_lengths_not_strings(caplog):
    """Test that edit operation logs old_len/new_len instead of old_string/new_string."""
    caplog.set_level(logging.INFO, logger="inspect_agents")

    old_string = "This old string should not appear in logs"
    new_string = "This new string should also not appear in logs"
    params = EditParams(
        command="edit", file_path="test.txt", old_string=old_string, new_string=new_string, replace_all=False
    )

    # This will fail during execution but we only care about the start logging
    try:
        await execute_edit(params)
    except Exception:
        pass  # Expected since file doesn't exist

    # Extract tool_event records
    events = []
    for rec in caplog.records:
        msg = rec.getMessage()
        if isinstance(msg, str) and msg.startswith("tool_event "):
            try:
                payload = json.loads(msg[len("tool_event ") :])
                events.append(payload)
            except Exception:
                pass

    # Find start event
    start_events = [e for e in events if e.get("phase") == "start" and e.get("tool") == "files:edit"]
    assert len(start_events) == 1

    start_event = start_events[0]
    args = start_event.get("args", {})

    # Verify length fields are present and string fields are not
    assert "old_len" in args
    assert "new_len" in args
    assert args["old_len"] == len(old_string)
    assert args["new_len"] == len(new_string)
    assert "replace_all" in args
    assert "old_string" not in args
    assert "new_string" not in args

    # Ensure original strings don't leak into logs
    joined = json.dumps(events)
    assert old_string not in joined
    assert new_string not in joined


@pytest.mark.asyncio
async def test_files_read_logs_metadata_not_content(caplog):
    """Test that read operation logs metadata without including file content."""
    caplog.set_level(logging.INFO, logger="inspect_agents")

    params = ReadParams(command="read", file_path="nonexistent.txt", offset=10, limit=50)

    # This will fail during execution but we only care about the start logging
    try:
        await execute_read(params)
    except Exception:
        pass  # Expected since file doesn't exist

    # Extract tool_event records
    events = []
    for rec in caplog.records:
        msg = rec.getMessage()
        if isinstance(msg, str) and msg.startswith("tool_event "):
            try:
                payload = json.loads(msg[len("tool_event ") :])
                events.append(payload)
            except Exception:
                pass

    # Find start event
    start_events = [e for e in events if e.get("phase") == "start" and e.get("tool") == "files:read"]
    assert len(start_events) == 1

    start_event = start_events[0]
    args = start_event.get("args", {})

    # Verify only metadata fields are present
    assert "file_path" in args
    assert "offset" in args
    assert "limit" in args
    assert "instance" in args
    assert args["file_path"] == "nonexistent.txt"
    assert args["offset"] == 10
    assert args["limit"] == 50

    # Verify no content-related fields
    assert "content" not in args
    assert "file_content" not in args

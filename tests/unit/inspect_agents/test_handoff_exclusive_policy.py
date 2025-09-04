#!/usr/bin/env python3
"""Unit test for handoff_exclusive_policy approver.

Validates that when a handoff tool is present in the assistant message,
only the first handoff is approved and non-handoff tools are skipped.
Also asserts that a repo-local logger event is emitted for skipped calls.
"""

import asyncio
import importlib
import json
import logging
import os
import sys

# Prefer vendored Inspect‑AI to avoid version drift with site‑packages
_VENDOR = os.path.join("external", "inspect_ai", "src")
if os.path.isdir(_VENDOR) and _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)

from inspect_ai.log._transcript import ToolEvent, Transcript, init_transcript, transcript  # noqa: E402
from inspect_ai.tool._tool_call import ToolCall  # noqa: E402

# Import approval module from this repo
approval = importlib.import_module('inspect_agents.approval')


class _Msg:
    def __init__(self, tool_calls):
        self.tool_calls = tool_calls


def _parse_tool_event_from_caplog(caplog: 'logging.LogCaptureFixture'):
    records = []
    for rec in caplog.records:
        msg = rec.getMessage()
        if not msg.startswith('tool_event '):
            continue
        try:
            payload = json.loads(msg.split('tool_event ', 1)[1])
            records.append(payload)
        except Exception:
            continue
    return records


def test_handoff_exclusive_skips_non_handoff(caplog):
    # Fresh transcript to make assertions deterministic
    init_transcript(Transcript())
    policies = approval.handoff_exclusive_policy()
    approver = policies[0].approver

    # Prepare assistant message containing a handoff and a non-handoff tool call
    handoff = ToolCall(id="1", function="transfer_to_researcher", arguments={})
    non_handoff = ToolCall(id="2", function="read_file", arguments={"file_path": "README.md"})
    msg = _Msg([handoff, non_handoff])
    history = [msg]

    # First handoff should be approved
    result1 = asyncio.run(approver(msg, handoff, None, history))
    assert getattr(result1, "decision", None) == "approve"

    # Non-handoff should be rejected and log a skipped event
    caplog.set_level(logging.INFO, logger="inspect_agents.tools")
    result2 = asyncio.run(approver(msg, non_handoff, None, history))
    assert getattr(result2, "decision", None) == "reject"
    assert "exclusivity" in (getattr(result2, "explanation", "") or "")

    events = _parse_tool_event_from_caplog(caplog)
    # Expect at least one handoff_exclusive skipped event
    assert any(e.get("tool") == "handoff_exclusive" and e.get("phase") == "skipped" for e in events)
    # Validate required fields
    matched = [e for e in events if e.get("tool") == "handoff_exclusive" and e.get("phase") == "skipped"]
    assert matched and matched[-1].get("selected_handoff_id") == "1" and matched[-1].get("skipped_function") == "read_file"

    # Optionally assert a standardized transcript ToolEvent for the skip
    tev = transcript().find_last_event(ToolEvent)
    if tev is not None:
        assert getattr(tev, "id", None) == "2"
        assert getattr(tev, "function", None) == "read_file"
        # Error should reflect a policy/approval skip and carry message
        assert getattr(tev, "error", None) is not None
        assert getattr(tev.error, "message", "").lower().startswith("skipped")
        # Metadata should include attribution for the selected handoff and the source
        assert isinstance(tev.metadata, dict)
        assert tev.metadata.get("selected_handoff_id") == "1"
        assert tev.metadata.get("skipped_function") == "read_file"
        assert tev.metadata.get("source") == "policy/handoff_exclusive"


def test_no_handoff_approves_everything():
    policies = approval.handoff_exclusive_policy()
    approver = policies[0].approver

    read_call = ToolCall(id="10", function="read_file", arguments={"file_path": "pyproject.toml"})
    msg = _Msg([read_call])
    history = [msg]

    result = asyncio.run(approver(msg, read_call, None, history))
    assert getattr(result, "decision", None) == "approve"

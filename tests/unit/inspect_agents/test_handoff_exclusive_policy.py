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
import sys
import types

# Minimal stubs for inspect_ai dependencies used by approval.py
approval_mod = types.ModuleType('inspect_ai.approval._approval')
class Approval:  # pragma: no cover - tiny shim
    def __init__(self, decision, modified=None, explanation=None):
        self.decision = decision
        self.modified = modified
        self.explanation = explanation
approval_mod.Approval = Approval
sys.modules['inspect_ai.approval._approval'] = approval_mod

policy_mod = types.ModuleType('inspect_ai.approval._policy')
class ApprovalPolicy:  # pragma: no cover - tiny shim
    def __init__(self, approver, tools):
        self.approver = approver
        self.tools = tools
policy_mod.ApprovalPolicy = ApprovalPolicy
sys.modules['inspect_ai.approval._policy'] = policy_mod

tool_mod = types.ModuleType('inspect_ai.tool._tool_call')
class ToolCall:  # pragma: no cover - tiny shim
    def __init__(self, id, function, arguments, parse_error=None, view=None, type=None):
        self.id = id
        self.function = function
        self.arguments = arguments
        self.parse_error = parse_error
        self.view = view
        self.type = type
tool_mod.ToolCall = ToolCall
sys.modules['inspect_ai.tool._tool_call'] = tool_mod

registry_mod = types.ModuleType('inspect_ai._util.registry')
class RegistryInfo:  # pragma: no cover - tiny shim
    def __init__(self, type, name):
        self.type = type
        self.name = name
def registry_tag(template, func, info):  # pragma: no cover - no-op
    pass
registry_mod.RegistryInfo = RegistryInfo
registry_mod.registry_tag = registry_tag
sys.modules['inspect_ai._util.registry'] = registry_mod


# Ensure our package path is available
if 'src' not in sys.path:
    sys.path.insert(0, 'src')

# Import approval module as a package module so relative imports work
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


def test_no_handoff_approves_everything():
    policies = approval.handoff_exclusive_policy()
    approver = policies[0].approver

    read_call = ToolCall(id="10", function="read_file", arguments={"file_path": "pyproject.toml"})
    msg = _Msg([read_call])
    history = [msg]

    result = asyncio.run(approver(msg, read_call, None, history))
    assert getattr(result, "decision", None) == "approve"

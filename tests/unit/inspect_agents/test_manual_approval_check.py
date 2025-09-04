#!/usr/bin/env python3
"""Tests mirroring scripts/manual_approval_check.py.

Covers:
- Sensitive tool name pattern checks
- Dev preset behavior (escalate vs approve)
- Prod preset behavior (terminate + redaction)
- Direct redaction helper behavior

This test imports approval.py directly with lightweight stubs for
inspect_ai internals to avoid importing the full package.
"""

import asyncio
import sys
import types


def _load_module_with_stubs():
    # ---- Minimal stubs for inspect_ai internals used by approval.py ----
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
        return None
    registry_mod.RegistryInfo = RegistryInfo
    registry_mod.registry_tag = registry_tag
    sys.modules['inspect_ai._util.registry'] = registry_mod

    # ---- Load the approval module directly to avoid package __init__ side-effects ----
    g = {}
    with open('src/inspect_agents/approval.py', encoding='utf-8') as f:
        code = f.read()
    exec(code, g, g)  # noqa: S102
    return g


def test_sensitive_patterns_and_dev_preset(approval_modules_guard):
    """Dev preset escalates for sensitive tool names, approves others."""
    mod = _load_module_with_stubs()
    policies = mod['approval_preset']("dev")
    dev_gate = policies[0].approver
    tool_call_cls = sys.modules['inspect_ai.tool._tool_call'].ToolCall

    cases = [
        ("write_file", True),
        ("text_editor", True),
        ("bash", True),
        ("python", True),
        ("web_browser_go", True),
        ("web_browser_click", True),
        ("web_browser", False),  # no underscore suffix → not sensitive
        ("safe_tool", False),
        ("read_file", False),
    ]

    for tool_name, should_escalate in cases:
        call = tool_call_cls(id="1", function=tool_name, arguments={})
        result = asyncio.run(dev_gate("", call, None, []))
        assert (result.decision == "escalate") == should_escalate, tool_name


def test_prod_preset_terminates_and_redacts(approval_modules_guard):
    """Prod preset terminates sensitive tools and redacts secrets in explanation."""
    mod = _load_module_with_stubs()
    policies = mod['approval_preset']("prod")
    prod_gate = policies[0].approver
    tool_call_cls = sys.modules['inspect_ai.tool._tool_call'].ToolCall

    args = {"code": "import os", "api_key": "SECRET_KEY", "authorization": "Bearer TOKEN"}
    call = tool_call_cls(id="1", function="python", arguments=args)
    result = asyncio.run(prod_gate("", call, None, []))
    assert result.decision == "terminate"
    explanation = result.explanation or ""
    assert "[REDACTED]" in explanation and "SECRET_KEY" not in explanation and "TOKEN" not in explanation


def test_redaction_helper_redacts_expected_keys(approval_modules_guard):
    """redact_arguments replaces sensitive fields with [REDACTED]."""
    original = {
        "file_path": "/etc/passwd",
        "api_key": "SECRET123",
        "content": "sensitive data",
        "authorization": "Bearer TOKEN",
        "normal_param": "ok",
    }

    mod = _load_module_with_stubs()
    red = mod['redact_arguments'](original)
    assert red["api_key"] == "[REDACTED]"
    assert red["content"] == "[REDACTED]"
    assert red["authorization"] == "[REDACTED]"
    # Non-sensitive values are preserved
    assert red["file_path"] == "/etc/passwd"
    assert red["normal_param"] == "ok"


# Cleanup handled by approval_modules_guard fixture

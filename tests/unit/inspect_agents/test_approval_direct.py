#!/usr/bin/env python3
"""Direct test for approval.py functionality."""

import asyncio
import re
import sys
import types


def _load_module_with_stubs():
    # Mock inspect_ai modules
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

    # Load approval.py directly
    g = {}
    with open('src/inspect_agents/approval.py', encoding='utf-8') as f:
        code = f.read()
    exec(code, g, g)
    return g

# Cleanup handled by approval_modules_guard fixture

def test_patterns(approval_modules_guard):
    """Sensitive regex matches expected tool names."""
    # Re-create the sensitive pattern from approval.py
    sensitive = re.compile(r"^(write_file|text_editor|bash|python|web_browser_)")

    cases = {
        "write_file": True,
        "text_editor": True,
        "bash": True,
        "python": True,
        "web_browser_go": True,
        "web_browser_click": True,
        "web_browser": False,  # Should not match without underscore suffix
        "safe_tool": False,
        "read_file": False,
    }

    for tool_name, expect in cases.items():
        assert bool(sensitive.match(tool_name)) == expect, f"regex mismatch for {tool_name}"

def test_dev_preset_behavior(approval_modules_guard):
    """Dev preset escalates sensitive tools, approves non-sensitive."""
    mod = _load_module_with_stubs()
    policies = mod['approval_preset']("dev")
    dev_gate = policies[0].approver
    tool_call_cls = sys.modules['inspect_ai.tool._tool_call'].ToolCall

    # python → escalate
    call = tool_call_cls(id="1", function="python", arguments={"code": "print('hello')"})
    result = asyncio.run(dev_gate("", call, None, []))
    assert result.decision == "escalate"

    # web_browser_go → escalate
    call = tool_call_cls(id="1", function="web_browser_go", arguments={"url": "https://example.com"})
    result = asyncio.run(dev_gate("", call, None, []))
    assert result.decision == "escalate"

    # read_file → approve
    call = tool_call_cls(id="1", function="read_file", arguments={"path": "/tmp/test.txt"})
    result = asyncio.run(dev_gate("", call, None, []))
    assert result.decision == "approve"

def test_prod_preset_behavior(approval_modules_guard):
    """Prod preset terminates sensitive tools and redacts secrets."""
    mod = _load_module_with_stubs()
    policies = mod['approval_preset']("prod")
    prod_gate = policies[0].approver
    tool_call_cls = sys.modules['inspect_ai.tool._tool_call'].ToolCall

    # python → terminate and redact
    args = {"code": "import os", "api_key": "SECRET_KEY", "authorization": "Bearer TOKEN"}
    call = tool_call_cls(id="1", function="python", arguments=args)
    result = asyncio.run(prod_gate("", call, None, []))
    assert result.decision == "terminate"
    explanation = result.explanation or ""
    assert "[REDACTED]" in explanation and "SECRET_KEY" not in explanation and "TOKEN" not in explanation

    # web_browser_go → terminate
    args = {"url": "https://example.com", "authorization": "Bearer SECRET"}
    call = tool_call_cls(id="1", function="web_browser_go", arguments=args)
    result = asyncio.run(prod_gate("", call, None, []))
    assert result.decision == "terminate"

if __name__ == "__main__":
    test_patterns()
    test_dev_preset_behavior() 
    test_prod_preset_behavior()
    print("\n=== Direct Test Complete ===")

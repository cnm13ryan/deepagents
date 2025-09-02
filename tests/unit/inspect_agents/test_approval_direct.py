#!/usr/bin/env python3
"""Direct test for approval.py functionality."""

import sys
import types
import asyncio
import json
import re

# Mock inspect_ai modules
approval_mod = types.ModuleType('inspect_ai.approval._approval')
class Approval:
    def __init__(self, decision, modified=None, explanation=None):
        self.decision = decision
        self.modified = modified
        self.explanation = explanation
approval_mod.Approval = Approval
sys.modules['inspect_ai.approval._approval'] = approval_mod

policy_mod = types.ModuleType('inspect_ai.approval._policy')
class ApprovalPolicy:
    def __init__(self, approver, tools):
        self.approver = approver
        self.tools = tools
policy_mod.ApprovalPolicy = ApprovalPolicy
sys.modules['inspect_ai.approval._policy'] = policy_mod

tool_mod = types.ModuleType('inspect_ai.tool._tool_call')
class ToolCall:
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
class RegistryInfo:
    def __init__(self, type, name):
        self.type = type
        self.name = name
def registry_tag(template, func, info):
    pass
registry_mod.RegistryInfo = RegistryInfo
registry_mod.registry_tag = registry_tag
sys.modules['inspect_ai._util.registry'] = registry_mod

# Load approval.py directly
exec(open('src/inspect_agents/approval.py').read())

def test_patterns():
    """Test that our updated regex patterns work correctly."""
    print("=== Testing Regex Patterns ===")
    
    # Re-create the sensitive pattern from approval.py
    sensitive = re.compile(r"^(write_file|text_editor|bash|python|web_browser_)")
    
    test_cases = [
        ("write_file", True),
        ("text_editor", True), 
        ("bash", True),
        ("python", True),
        ("web_browser_go", True),
        ("web_browser_click", True),
        ("web_browser", False),  # Should not match without underscore
        ("safe_tool", False),
        ("read_file", False),
    ]
    
    for tool_name, should_match in test_cases:
        is_match = bool(sensitive.match(tool_name))
        status = "✓" if is_match == should_match else "✗"
        print(f"{status} {tool_name}: {'matches' if is_match else 'no match'} (expected: {'matches' if should_match else 'no match'})")

def test_dev_preset_behavior():
    """Test dev preset behavior."""
    print("\n=== Testing Dev Preset Behavior ===")
    
    policies = approval_preset("dev")
    dev_gate = policies[0].approver
    
    # Test python tool (should escalate)
    call = ToolCall(id="1", function="python", arguments={"code": "print('hello')"})
    result = asyncio.run(dev_gate("", call, None, []))
    status = "✓" if result.decision == "escalate" else "✗"
    print(f"{status} python: {result.decision} (expected: escalate)")
    
    # Test web_browser_go (should escalate)
    call = ToolCall(id="1", function="web_browser_go", arguments={"url": "https://example.com"})
    result = asyncio.run(dev_gate("", call, None, []))
    status = "✓" if result.decision == "escalate" else "✗"
    print(f"{status} web_browser_go: {result.decision} (expected: escalate)")
    
    # Test read_file (should approve)
    call = ToolCall(id="1", function="read_file", arguments={"path": "/tmp/test.txt"})
    result = asyncio.run(dev_gate("", call, None, []))
    status = "✓" if result.decision == "approve" else "✗"
    print(f"{status} read_file: {result.decision} (expected: approve)")

def test_prod_preset_behavior():
    """Test prod preset behavior with redaction."""
    print("\n=== Testing Prod Preset Behavior ===")
    
    policies = approval_preset("prod")
    prod_gate = policies[0].approver
    
    # Test python with sensitive args (should terminate and redact)
    args = {"code": "import os", "api_key": "SECRET_KEY", "authorization": "Bearer TOKEN"}
    call = ToolCall(id="1", function="python", arguments=args)
    result = asyncio.run(prod_gate("", call, None, []))
    
    status1 = "✓" if result.decision == "terminate" else "✗"
    print(f"{status1} python termination: {result.decision} (expected: terminate)")
    
    explanation = result.explanation or ""
    has_redacted = "[REDACTED]" in explanation
    has_secrets = "SECRET_KEY" in explanation or "TOKEN" in explanation
    status2 = "✓" if has_redacted and not has_secrets else "✗"
    print(f"{status2} redaction: has [REDACTED]={has_redacted}, has secrets={has_secrets}")
    
    # Test web_browser_go with auth (should terminate and redact)
    args = {"url": "https://example.com", "authorization": "Bearer SECRET"}
    call = ToolCall(id="1", function="web_browser_go", arguments=args)
    result = asyncio.run(prod_gate("", call, None, []))
    
    status3 = "✓" if result.decision == "terminate" else "✗"
    print(f"{status3} web_browser_go termination: {result.decision} (expected: terminate)")

if __name__ == "__main__":
    test_patterns()
    test_dev_preset_behavior() 
    test_prod_preset_behavior()
    print("\n=== Direct Test Complete ===")

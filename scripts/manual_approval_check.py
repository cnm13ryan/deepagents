#!/usr/bin/env python3
# ruff: noqa: E402, E501
"""Manual test for approval patterns.

Run with:
  CI=1 NO_NETWORK=1 PYTHONPATH=src python scripts/manual_approval_check.py
"""

import sys
import types
import asyncio

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

# Import the approval module
from src.inspect_agents.approval import approval_preset, redact_arguments

def test_patterns():
    """Test that our updated regex patterns work correctly."""
    print("=== Testing Regex Patterns ===")
    
    # Test cases for sensitive tools
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
        # Get dev preset policies
        policies = approval_preset("dev")
        dev_gate = policies[0].approver
        
        call = ToolCall(id="1", function=tool_name, arguments={})
        result = asyncio.run(dev_gate("", call, None, []))
        
        is_sensitive = result.decision == "escalate"
        status = "✓" if is_sensitive == should_match else "✗"
        print(f"{status} {tool_name}: {'sensitive' if is_sensitive else 'approved'} (expected: {'sensitive' if should_match else 'approved'})")

def test_dev_preset():
    """Test dev preset escalates sensitive tools."""
    print("\n=== Testing Dev Preset ===")
    
    policies = approval_preset("dev")
    
    # Test sensitive tool (should escalate)
    call = ToolCall(id="1", function="python", arguments={"code": "print('hello')"})
    dev_gate = policies[0].approver
    result = asyncio.run(dev_gate("", call, None, []))
    print(f"Dev gate for 'python': {result.decision} (expected: escalate)")
    
    # Test non-sensitive tool (should approve)  
    call = ToolCall(id="1", function="read_file", arguments={"path": "/tmp/test.txt"})
    result = asyncio.run(dev_gate("", call, None, []))
    print(f"Dev gate for 'read_file': {result.decision} (expected: approve)")

def test_prod_preset():
    """Test prod preset terminates sensitive tools with redaction."""
    print("\n=== Testing Prod Preset ===")
    
    policies = approval_preset("prod")
    prod_gate = policies[0].approver
    
    # Test sensitive tool with secrets (should terminate and redact)
    args = {"code": "import os", "api_key": "SECRET_KEY", "authorization": "Bearer TOKEN"}
    call = ToolCall(id="1", function="python", arguments=args)
    result = asyncio.run(prod_gate("", call, None, []))
    
    print(f"Prod gate for 'python': {result.decision} (expected: terminate)")
    explanation = result.explanation or ""
    has_redacted = "[REDACTED]" in explanation
    has_secrets = "SECRET_KEY" in explanation or "TOKEN" in explanation
    print(f"Explanation contains [REDACTED]: {has_redacted}")
    print(f"Explanation contains secrets: {has_secrets}")
    print(f"Redaction working correctly: {has_redacted and not has_secrets}")

def test_redaction():
    """Test argument redaction."""
    print("\n=== Testing Redaction ===")
    
    test_args = {
        "file_path": "/etc/passwd", 
        "api_key": "SECRET123",
        "content": "sensitive data",
        "authorization": "Bearer TOKEN",
        "normal_param": "safe_value"
    }
    
    redacted = redact_arguments(test_args)
    print("Original args:", test_args)
    print("Redacted args:", redacted)
    
    expected_redacted = ["api_key", "content", "authorization"]
    for key in expected_redacted:
        if redacted.get(key) == "[REDACTED]":
            print(f"✓ {key} properly redacted")
        else:
            print(f"✗ {key} NOT redacted: {redacted.get(key)}")

if __name__ == "__main__":
    test_patterns()
    test_dev_preset() 
    test_prod_preset()
    test_redaction()
    print("\n=== Manual Test Complete ===")

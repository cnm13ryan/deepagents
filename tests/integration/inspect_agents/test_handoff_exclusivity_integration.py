#!/usr/bin/env python3
"""Integration test: real policy_approver + handoff exclusivity.

This test wires Inspect-AI's real `policy_approver` to the repo's
`handoff_exclusive_policy()` and verifies behavior on a mixed batch:
first handoff approves; subsequent handoffs and non-handoff tools reject.

Note: This test exercises the exclusivity policy in isolation (without
dev/prod preset gates) to validate core semantics with the real policy engine.
"""

import asyncio
import sys

import pytest

pytestmark = pytest.mark.handoff

def _ensure_vendor_on_path():
    # Prefer vendored Inspect-AI over any site-packages version
    vendor_src = 'external/inspect_ai/src'
    if vendor_src not in sys.path:
        sys.path.insert(0, vendor_src)


def _load_approval_module_symbols():
    # Load approval.py directly to avoid importing the entire package
    g: dict[str, object] = {}
    with open('src/inspect_agents/approval.py', encoding='utf-8') as f:
        code = f.read()
    exec(code, g, g)
    return g['handoff_exclusive_policy']  # type: ignore[index]


def test_policy_approver_enforces_exclusivity_on_mixed_batch():
    _ensure_vendor_on_path()

    # Import real policy engine and tool/message types from vendored Inspect-AI
    from inspect_ai.approval._policy import policy_approver
    from inspect_ai.model._chat_message import ChatMessageAssistant
    from inspect_ai.tool._tool_call import ToolCall

    # Build policies using the repo's exclusivity approver
    handoff_exclusive_policy = _load_approval_module_symbols()
    policies = handoff_exclusive_policy()
    approver = policy_approver(policies)

    # Compose assistant message with a mixed batch
    calls = [
        ToolCall(id='1', function='transfer_to_researcher', arguments={}),
        ToolCall(id='2', function='transfer_to_writer', arguments={}),
        ToolCall(id='3', function='read_file', arguments={'file_path': 'README.md'}),
    ]
    msg = ChatMessageAssistant(content='', tool_calls=calls)
    history = [msg]

    # First handoff approved
    ok1 = asyncio.run(approver('', calls[0], None, history))
    assert getattr(ok1, 'decision', None) == 'approve'

    # Second handoff rejected due to exclusivity
    ok2 = asyncio.run(approver('', calls[1], None, history))
    assert getattr(ok2, 'decision', None) == 'reject'
    assert 'exclusivity' in (getattr(ok2, 'explanation', '') or '')

    # Non-handoff rejected when a handoff is present in the batch
    ok3 = asyncio.run(approver('', calls[2], None, history))
    assert getattr(ok3, 'decision', None) == 'reject'
    assert 'exclusivity' in (getattr(ok3, 'explanation', '') or '')

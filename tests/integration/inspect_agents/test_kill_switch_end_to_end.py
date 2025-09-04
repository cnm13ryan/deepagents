#!/usr/bin/env python3
"""Integration: execute_tools + parallel kill-switch end-to-end.

Asserts that with the kill-switch enabled and multiple non-handoff tool calls
in a single assistant turn, only the first tool executes successfully and
subsequent tools are rejected, with standardized transcript events emitted.
"""

import asyncio
import os
import sys
import types


def _ensure_vendor_on_path():
    vendor_src = "external/inspect_ai/src"
    if vendor_src not in sys.path:
        sys.path.insert(0, vendor_src)


def _ensure_apply_shim():
    # Provide a lightweight apply shim (mirrors the handoff end-to-end test)
    import fnmatch
    import sys as _sys

    apply_mod = types.ModuleType("inspect_ai.approval._apply")
    _compiled: list[tuple[list[str], object]] = []

    def init_tool_approval(policies):  # pragma: no cover - simple wiring
        nonlocal _compiled
        compiled: list[tuple[list[str], object]] = []
        if policies:
            for p in policies:
                tools = getattr(p, "tools", "*")
                approver = getattr(p, "approver", None)
                patterns = tools if isinstance(tools, list) else [tools]
                compiled.append((patterns, approver))
        _compiled = compiled

    async def apply_tool_approval(message, call, viewer, history):
        approver = None
        if _compiled:
            for patterns, ap in _compiled:
                for pat in patterns:
                    pat = pat if pat.endswith("*") else pat + "*"
                    if fnmatch.fnmatch(call.function, pat):
                        approver = ap
                        break
                if approver:
                    break
        if approver is None:
            class _Approval:
                decision = "approve"
                modified = None
                explanation = None
            return True, _Approval()
        view = viewer(call) if callable(viewer) else None
        approval = await approver(message, call, view, history)  # type: ignore[misc]
        return (getattr(approval, "decision", None) in ("approve", "modify")), approval

    apply_mod.init_tool_approval = init_tool_approval
    apply_mod.apply_tool_approval = apply_tool_approval
    _sys.modules["inspect_ai.approval._apply"] = apply_mod


def test_kill_switch_only_first_tool_executes(monkeypatch):
    _ensure_vendor_on_path()

    # Enable kill-switch via canonical backlog env var
    monkeypatch.setenv("INSPECT_DISABLE_TOOL_PARALLEL", "1")

    from inspect_ai.model._call_tools import execute_tools
    from inspect_ai.model._chat_message import ChatMessageAssistant, ChatMessageTool, ChatMessageUser
    from inspect_ai.tool._tool import Tool
    from inspect_ai.tool._tool_call import ToolCall
    from inspect_ai.tool._tool_def import ToolDef
    from inspect_ai.tool._tool_params import ToolParams
    from inspect_ai.log._transcript import ToolEvent, Transcript, init_transcript, transcript

    from inspect_agents.approval import parallel_kill_switch_policy

    _ensure_apply_shim()
    from inspect_ai.approval._apply import init_tool_approval

    # Activate only the kill-switch policy
    init_tool_approval(parallel_kill_switch_policy())
    init_transcript(Transcript())

    # Two trivial non-handoff echo tools
    def _echo(name: str, text: str) -> Tool:
        async def execute() -> str:
            return text

        params = ToolParams()
        return ToolDef(execute, name=name, description=f"Echo {text}", parameters=params).as_tool()

    echo_a = _echo("echo_a", "A")
    echo_b = _echo("echo_b", "B")

    # Assistant emits two tool calls
    messages = [
        ChatMessageUser(content="start"),
        ChatMessageAssistant(
            content="",
            tool_calls=[
                ToolCall(id="1", function="echo_a", arguments={}),
                ToolCall(id="2", function="echo_b", arguments={}),
            ],
        ),
    ]

    result = asyncio.run(execute_tools(messages, [echo_a, echo_b]))

    # Exactly one successful tool result (the first)
    tool_msgs = [m for m in result.messages if isinstance(m, ChatMessageTool)]
    successes = [m for m in tool_msgs if getattr(m, "error", None) is None]
    assert len(successes) == 1 and successes[0].function == "echo_a"

    # Transcript should include one skipped event for the second call
    events = transcript().events
    skipped = [
        e
        for e in events
        if isinstance(e, ToolEvent)
        and getattr(e, "error", None) is not None
        and getattr(e, "metadata", None) is not None
        and e.metadata.get("source") == "policy/parallel_kill_switch"
        and e.metadata.get("first_allowed_id") == "1"
        and e.metadata.get("skipped_function") == "echo_b"
    ]
    assert len(skipped) == 1

    # Cleanup env
    monkeypatch.delenv("INSPECT_DISABLE_TOOL_PARALLEL", raising=False)

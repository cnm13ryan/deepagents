import asyncio
import sys
import types

import pytest

# Use the real Inspect‑AI ToolCall dataclass to satisfy event schema
from inspect_ai.tool._tool_call import ToolCall

# Provide minimal policy module if not present
if 'inspect_ai.approval._policy' not in sys.modules:
    import types
    pol = types.ModuleType('inspect_ai.approval._policy')
    sys.modules['inspect_ai.approval._policy'] = pol

from inspect_ai.approval._policy import policy_approver  # type: ignore  # noqa: E402

from inspect_agents.approval import approval_preset  # noqa: E402


def _install_apply_shim_with_policy():
    """Ensure approval engine symbols exist without leaking stubs globally.

    Prefer the real vendored Inspect‑AI modules. Only install minimal fallbacks
    if imports fail (e.g., when running in isolation without vendor).
    """
    # Try to import the real apply + policy and verify expected symbols.
    try:  # pragma: no cover - exercised indirectly by import side effects
        from inspect_ai.approval import _apply as _real_apply
        from inspect_ai.approval._policy import policy_approver  # noqa: F401
        if hasattr(_real_apply, "init_tool_approval") and hasattr(
            _real_apply, "apply_tool_approval"
        ):
            return
    except Exception:
        pass

    # Minimal local fallback policy_approver and apply module (scoped)
    import fnmatch

    def policy_approver(policies):  # type: ignore[no-redef]
        def matches(call, tools):
            pats = tools if isinstance(tools, list) else [tools]
            return any(
                fnmatch.fnmatch(call.function, p if p.endswith("*") else p + "*")
                for p in pats
            )

        async def approve(message, call, view, history):
            for pol in policies:
                if matches(call, pol.tools):
                    ap = await pol.approver(message, call, view, history)
                    if getattr(ap, "decision", None) != "escalate":
                        return ap
            # default reject
            class _A:
                pass

            a = _A()
            a.decision = "reject"
            a.explanation = "No approver"
            a.modified = None
            return a

        return approve

    apply_mod = types.ModuleType("inspect_ai.approval._apply")
    _approver_ref = {"fn": None}

    def init_tool_approval(policies):
        _approver_ref["fn"] = policy_approver(policies) if policies else None

    async def apply_tool_approval(message, call, viewer, history):
        if _approver_ref["fn"] is None:
            class _Approval:
                decision = "approve"
                modified = None
                explanation = None

            return True, _Approval()
        view = viewer(call) if viewer else None
        approval = await _approver_ref["fn"](message, call, view, history)
        return (approval.decision in ("approve", "modify")), approval

    apply_mod.init_tool_approval = init_tool_approval
    apply_mod.apply_tool_approval = apply_tool_approval
    # Register/override fallback apply module (avoid leaking broken stubs)
    sys.modules["inspect_ai.approval._apply"] = apply_mod
    if "inspect_ai.approval._approval" not in sys.modules:
        appr = types.ModuleType("inspect_ai.approval._approval")
        class Approval:  # minimal constructor compatibility
            def __init__(self, decision, modified=None, explanation=None):
                self.decision = decision
                self.modified = modified
                self.explanation = explanation

        setattr(appr, "Approval", Approval)
        sys.modules["inspect_ai.approval._approval"] = appr
    if "inspect_ai.approval._policy" not in sys.modules:
        pol = types.ModuleType("inspect_ai.approval._policy")
        class ApprovalPolicy:  # minimal constructor compatibility
            def __init__(self, approver, tools):
                self.approver = approver
                self.tools = tools

        setattr(pol, "ApprovalPolicy", ApprovalPolicy)
        sys.modules["inspect_ai.approval._policy"] = pol


def test_ci_preset_auto_approves():
    _install_apply_shim_with_policy()
    policies = approval_preset("ci")
    approver = policy_approver(policies)
    approval = asyncio.run(approver("", ToolCall(id="1", function="write_file", arguments={}), None, []))
    ok = getattr(approval, "decision", None) in ("approve", "modify")
    assert ok is True


def test_dev_preset_escalates_then_rejects():
    _install_apply_shim_with_policy()
    policies = approval_preset("dev")
    approver = policy_approver(policies)
    approval = asyncio.run(approver("", ToolCall(id="1", function="write_file", arguments={}), None, []))
    ok = getattr(approval, "decision", None) in ("approve", "modify")
    assert ok is False
    assert getattr(approval, "decision", None) == "reject"


def test_prod_preset_terminates_sensitive_and_redacts():
    _install_apply_shim_with_policy()
    policies = approval_preset("prod")
    approver = policy_approver(policies)
    args = {"file_path": "/etc/passwd", "api_key": "SECRET", "file_text": "X"}
    approval = asyncio.run(approver("", ToolCall(id="1", function="write_file", arguments=args), None, []))
    ok = getattr(approval, "decision", None) in ("approve", "modify")
    assert ok is False
    assert getattr(approval, "decision", None) == "terminate"
    # Explanation should carry redacted args
    text = getattr(approval, "explanation", "")
    assert "[REDACTED]" in text and "SECRET" not in text


def test_dev_preset_escalates_python_then_rejects():
    _install_apply_shim_with_policy()
    policies = approval_preset("dev")
    approver = policy_approver(policies)
    approval = asyncio.run(approver("", ToolCall(id="1", function="python", arguments={}), None, []))
    ok = getattr(approval, "decision", None) in ("approve", "modify")
    assert ok is False
    assert getattr(approval, "decision", None) == "reject"


def test_dev_preset_escalates_web_browser_go_then_rejects():
    _install_apply_shim_with_policy()
    policies = approval_preset("dev")
    approval = asyncio.run(policy_approver(policies)("", ToolCall(id="1", function="web_browser_go", arguments={}), None, []))
    ok = getattr(approval, "decision", None) in ("approve", "modify")
    assert ok is False
    assert getattr(approval, "decision", None) == "reject"


def test_prod_preset_terminates_python_with_redacted_args():
    _install_apply_shim_with_policy()
    policies = approval_preset("prod")
    approver = policy_approver(policies)
    args = {"code": "import os; os.system('rm -rf /')", "api_key": "SECRET"}
    approval = asyncio.run(approver("", ToolCall(id="1", function="python", arguments=args), None, []))
    ok = getattr(approval, "decision", None) in ("approve", "modify")
    assert ok is False
    assert getattr(approval, "decision", None) == "terminate"
    text = getattr(approval, "explanation", "")
    assert "[REDACTED]" in text and "SECRET" not in text


def test_prod_preset_terminates_web_browser_go_with_redacted_args():
    _install_apply_shim_with_policy()
    policies = approval_preset("prod")
    approver = policy_approver(policies)
    args = {"url": "https://malicious.example.com", "authorization": "Bearer SECRET_TOKEN"}
    approval = asyncio.run(approver("", ToolCall(id="1", function="web_browser_go", arguments=args), None, []))
    ok = getattr(approval, "decision", None) in ("approve", "modify")
    assert ok is False
    assert getattr(approval, "decision", None) == "terminate"
    text = getattr(approval, "explanation", "")
    assert "[REDACTED]" in text and "SECRET_TOKEN" not in text
pytestmark = pytest.mark.approvals

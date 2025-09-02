import asyncio
import sys
import types

from inspect_ai.tool._tool_call import ToolCall

# Provide minimal policy module if not present
if 'inspect_ai.approval._policy' not in sys.modules:
    import types
    pol = types.ModuleType('inspect_ai.approval._policy')
    sys.modules['inspect_ai.approval._policy'] = pol

from inspect_agents.approval import approval_preset


def _install_apply_shim_with_policy():
    # Ensure approval policy engine available
    # Import real function from vendored source
    try:
        from inspect_ai.approval._policy import policy_approver  # type: ignore
    except Exception:
        # Minimal local fallback policy_approver
        import fnmatch
        def policy_approver(policies):
            def matches(call, tools):
                pats = tools if isinstance(tools, list) else [tools]
                return any(fnmatch.fnmatch(call.function, p if p.endswith('*') else p+'*') for p in pats)
            async def approve(message, call, view, history):
                for pol in policies:
                    if matches(call, pol.tools):
                        ap = await pol.approver(message, call, view, history)
                        if getattr(ap, 'decision', None) != 'escalate':
                            return ap
                # default reject
                class _A: pass
                a=_A(); a.decision='reject'; a.explanation='No approver'; a.modified=None
                return a
            return approve

    apply_mod = types.ModuleType("inspect_ai.approval._apply")
    _approver_ref = {"fn": None}

    def init_tool_approval(policies):
        _approver_ref["fn"] = policy_approver(policies) if policies else None

    async def apply_tool_approval(message, call, viewer, history):
        if _approver_ref["fn"] is None:
            class _Approval: decision = "approve"; modified=None; explanation=None
            return True, _Approval()
        view = viewer(call) if viewer else None
        approval = await _approver_ref["fn"](message, call, view, history)
        return (approval.decision in ("approve","modify")), approval

    apply_mod.init_tool_approval = init_tool_approval
    apply_mod.apply_tool_approval = apply_tool_approval
    sys.modules["inspect_ai.approval._apply"] = apply_mod
    # minimal approval._approval for Approval class used by presets
    if 'inspect_ai.approval._approval' not in sys.modules:
        appr = types.ModuleType('inspect_ai.approval._approval')
        class Approval:
            def __init__(self, decision, modified=None, explanation=None):
                self.decision=decision; self.modified=modified; self.explanation=explanation
        sys.modules['inspect_ai.approval._approval']=appr; setattr(appr,'Approval',Approval)
    # minimal approval._policy for ApprovalPolicy dataclass used by presets
    if 'inspect_ai.approval._policy' not in sys.modules:
        pol = types.ModuleType('inspect_ai.approval._policy')
        class ApprovalPolicy:  # minimal constructor compatibility
            def __init__(self, approver, tools): self.approver=approver; self.tools=tools
        setattr(pol,'ApprovalPolicy',ApprovalPolicy)
        sys.modules['inspect_ai.approval._policy'] = pol


def test_ci_preset_auto_approves():
    _install_apply_shim_with_policy()
    policies = approval_preset("ci")
    from inspect_ai.approval._apply import apply_tool_approval, init_tool_approval
    init_tool_approval(policies)
    ok, approval = asyncio.run(apply_tool_approval("", ToolCall(id="1", function="write_file", arguments={}), None, []))
    assert ok is True


def test_dev_preset_escalates_then_rejects():
    _install_apply_shim_with_policy()
    policies = approval_preset("dev")
    from inspect_ai.approval._apply import apply_tool_approval, init_tool_approval
    init_tool_approval(policies)
    ok, approval = asyncio.run(apply_tool_approval("", ToolCall(id="1", function="write_file", arguments={}), None, []))
    assert ok is False
    assert getattr(approval, "decision", None) == "reject"


def test_prod_preset_terminates_sensitive_and_redacts():
    _install_apply_shim_with_policy()
    policies = approval_preset("prod")
    from inspect_ai.approval._apply import apply_tool_approval, init_tool_approval
    init_tool_approval(policies)
    args = {"file_path": "/etc/passwd", "api_key": "SECRET", "file_text": "X"}
    ok, approval = asyncio.run(apply_tool_approval("", ToolCall(id="1", function="write_file", arguments=args), None, []))
    assert ok is False
    assert getattr(approval, "decision", None) == "terminate"
    # Explanation should carry redacted args
    text = getattr(approval, "explanation", "")
    assert "[REDACTED]" in text and "SECRET" not in text

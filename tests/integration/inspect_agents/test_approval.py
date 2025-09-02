import asyncio
import sys
import types

import pytest

from inspect_ai.agent._agent import AgentState, agent
from inspect_ai.model._chat_message import ChatMessageAssistant
from inspect_ai.tool._tool_call import ToolCall
from inspect_ai._util.exception import TerminateSampleError

from inspect_agents.agents import build_supervisor
from inspect_agents.approval import approval_from_interrupt_config
from inspect_agents.run import run_agent


def _install_apply_shim():
    """Override inspect_ai.approval._apply to support policies in tests.

    Provides `init_tool_approval(policies)` and `apply_tool_approval(...)` that
    delegate to `policy_approver`.
    """
    # Ensure inspect_ai.approval is a package so submodules load
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[2]
    approval_pkg_path = repo_root / "external" / "inspect_ai" / "src" / "inspect_ai" / "approval"
    if "inspect_ai.approval" not in sys.modules:
        pkg = types.ModuleType("inspect_ai.approval")
        pkg.__path__ = [str(approval_pkg_path)]  # type: ignore[attr-defined]
        sys.modules["inspect_ai.approval"] = pkg
    else:
        # ensure path exists for submodule discovery
        mod = sys.modules["inspect_ai.approval"]
        if not hasattr(mod, "__path__"):
            mod.__path__ = [str(approval_pkg_path)]  # type: ignore[attr-defined]

    # Provide lightweight stubs to avoid heavy deps
    if "inspect_ai._util.config" not in sys.modules:
        cfg_stub = types.ModuleType("inspect_ai._util.config")
        def read_config_object(_path):  # pragma: no cover
            return {}
        cfg_stub.read_config_object = read_config_object
        sys.modules["inspect_ai._util.config"] = cfg_stub
    if "inspect_ai.util._resource" not in sys.modules:
        res_stub = types.ModuleType("inspect_ai.util._resource")
        def resource(path, type="file"):  # pragma: no cover
            return path
        res_stub.resource = resource
        sys.modules["inspect_ai.util._resource"] = res_stub
    # Ensure transcript has ApprovalEvent for logging
    if "inspect_ai.log._transcript" in sys.modules:
        tmod = sys.modules["inspect_ai.log._transcript"]
        if not hasattr(tmod, "ApprovalEvent"):
            class ApprovalEvent:  # pragma: no cover
                def __init__(self, **kwargs):
                    for k, v in kwargs.items():
                        setattr(self, k, v)
            setattr(tmod, "ApprovalEvent", ApprovalEvent)

    apply_mod = types.ModuleType("inspect_ai.approval._apply")
    _approver_ref = {"fn": None}

    def init_tool_approval(policies):  # pragma: no cover - simple wiring
        compiled = []
        if policies:
            for p in policies:
                tools = getattr(p, "tools", "*")
                approver = getattr(p, "approver", None)
                patterns = tools if isinstance(tools, list) else [tools]
                compiled.append((patterns, approver))
        _approver_ref["fn"] = compiled

    async def apply_tool_approval(message, call, viewer, history):
        compiled = _approver_ref["fn"]
        approver = None
        if compiled:
            import fnmatch

            for patterns, ap in compiled:
                for pat in patterns:
                    pat = pat if pat.endswith("*") else pat + "*"
                    if fnmatch.fnmatch(call.function, pat):
                        approver = ap
                        break
                if approver:
                    break

        if approver is None:
            class _Rej:
                decision = "reject"
                modified = None
                explanation = "No approver"
            return False, _Rej()

        view = viewer(call) if viewer else None
        approval = await approver(message, call, view, history)
        try:
            with open("approval_debug.log", "a") as fp:  # pragma: no cover - debug
                fp.write(f"decision={getattr(approval,'decision',None)}\n")
        except Exception:
            pass
        if getattr(approval, "decision", None) in ("approve", "modify"):
            return True, approval
        return False, approval

    apply_mod.init_tool_approval = init_tool_approval
    apply_mod.apply_tool_approval = apply_tool_approval
    sys.modules["inspect_ai.approval._apply"] = apply_mod


@agent
def submit_model():
    async def execute(state: AgentState, tools):
        # Single submit call; approval policies target this tool
        state.messages.append(
            ChatMessageAssistant(
                content="",  # content intentionally unused
                tool_calls=[
                    ToolCall(id="1", function="submit", arguments={"answer": "DONE"})
                ],
            )
        )
        return state

    return execute


def _supervisor():
    return build_supervisor(
        prompt="You are helpful.", tools=[], attempts=1, model=submit_model()
    )


def test_approve_allows_original_args():
    _install_apply_shim()
    policies = approval_from_interrupt_config({"submit": {"decision": "approve"}})
    agent_obj = _supervisor()

    result = asyncio.run(run_agent(agent_obj, "start", approval=policies))
    assert "DONE" in (result.output.completion or "")


def test_modify_changes_arguments_before_execution():
    _install_apply_shim()
    policies = approval_from_interrupt_config(
        {"submit": {"decision": "modify", "modified_args": {"answer": "CHANGED"}}}
    )
    agent_obj = _supervisor()

    result = asyncio.run(run_agent(agent_obj, "go", approval=policies))
    assert "CHANGED" in (result.output.completion or "")


def test_reject_returns_not_approved_and_decision():
    _install_apply_shim()
    policies = approval_from_interrupt_config({"submit": {"decision": "reject"}})
    # Activate policies and call the shim directly to avoid agent loop
    apply_mod = sys.modules["inspect_ai.approval._apply"]
    apply_mod.init_tool_approval(policies)
    # Construct a simple ToolCall for submit
    call = ToolCall(id="1", function="submit", arguments={"answer": "X"})
    approved, approval = asyncio.run(apply_mod.apply_tool_approval("", call, None, []))
    assert approved is False
    assert getattr(approval, "decision", None) == "reject"


def test_terminate_aborts_sample():
    _install_apply_shim()
    policies = approval_from_interrupt_config({"submit": {"decision": "terminate"}})
    agent_obj = _supervisor()

    with pytest.raises(TerminateSampleError):
        asyncio.run(run_agent(agent_obj, "go", approval=policies))


def teardown_module(module):  # reset approval shim to default approve-all
    import types
    import sys
    apply_mod = types.ModuleType("inspect_ai.approval._apply")
    async def apply_tool_approval(message, call, viewer, history):  # pragma: no cover
        class _Approval:
            decision = "approve"
            modified = None
            explanation = None
        return True, _Approval()
    apply_mod.apply_tool_approval = apply_tool_approval
    sys.modules["inspect_ai.approval._apply"] = apply_mod

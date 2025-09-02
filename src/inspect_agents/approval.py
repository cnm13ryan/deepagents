from __future__ import annotations

import json
import re
from typing import Any


def approval_from_interrupt_config(cfg: dict[str, Any]) -> list[Any]:
    """Convert deepagents interrupt config to Inspect ApprovalPolicy list.

    Mapping rules:
    - Keys = tool name or glob pattern.
    - Values may be `True` (use defaults) or a dict with optional keys:
      - allow_accept (default True), allow_edit (default True), allow_ignore (default False)
      - decision: one of {approve, modify, reject, terminate} [test convenience]
      - modified_args / modify_args: dict of new tool arguments when decision==modify
      - modified_function / modify_function: optional new tool function name when decision==modify
      - explanation: optional explanation string
    - allow_ignore=True is unsupported and raises ValueError (parity with deepagents).
    """
    from inspect_ai.approval._approval import Approval  # type: ignore
    try:
        from inspect_ai.approval._policy import ApprovalPolicy  # type: ignore
    except Exception:
        class ApprovalPolicy:  # type: ignore
            def __init__(self, approver, tools):
                self.approver = approver
                self.tools = tools
    from inspect_ai._util.registry import RegistryInfo, registry_tag  # type: ignore
    from inspect_ai.tool._tool_call import ToolCall  # type: ignore

    policies: list[ApprovalPolicy] = []

    for tool, conf in (cfg or {}).items():
        conf_dict = conf if isinstance(conf, dict) else {}

        allow_accept = bool(conf_dict.get("allow_accept", True))
        allow_edit = bool(conf_dict.get("allow_edit", True))
        allow_ignore = bool(conf_dict.get("allow_ignore", False))
        if allow_ignore:
            raise ValueError("allow_ignore=True not supported by Inspect approvals")

        decision: str = conf_dict.get("decision", "approve")
        explanation: str | None = conf_dict.get("explanation")
        # Support either key spellings for modified fields
        mod_args = conf_dict.get("modified_args", conf_dict.get("modify_args"))
        mod_fn = conf_dict.get("modified_function", conf_dict.get("modify_function"))

        async def _approve(message, call: ToolCall, view, history):  # type: ignore[no-redef]
            dec = decision
            if dec == "approve":
                if not allow_accept:
                    return Approval(decision="reject", explanation=explanation or "accept not allowed")
                return Approval(decision="approve", explanation=explanation)
            elif dec == "modify":
                if not allow_edit:
                    return Approval(decision="reject", explanation=explanation or "edit not allowed")
                new_call = call
                if mod_args is not None or mod_fn is not None:
                    new_call = ToolCall(
                        id=call.id,
                        function=(mod_fn or call.function),
                        arguments=(mod_args or call.arguments),
                        parse_error=call.parse_error,
                        view=call.view,
                        type=call.type,
                    )
                return Approval(decision="modify", modified=new_call, explanation=explanation)
            elif dec == "reject":
                return Approval(decision="reject", explanation=explanation)
            elif dec == "terminate":
                return Approval(decision="terminate", explanation=explanation)
            else:
                return Approval(decision="approve", explanation=explanation)

        # Attach registry info so Inspect can log without error
        registry_tag(
            lambda: None,  # signature template without required args
            _approve,
            RegistryInfo(type="approver", name=f"inline/{tool}"),
        )

        policies.append(ApprovalPolicy(approver=_approve, tools=tool))

    return policies


def activate_approval_policies(policies: list[Any] | None) -> None:
    """Call Inspect's init_tool_approval with given policies if available.

    Safe no-op if the apply module is stubbed without init.
    """
    if not policies:
        return
    try:
        from inspect_ai.approval._apply import init_tool_approval  # type: ignore

        init_tool_approval(policies)
    except Exception:
        # Tests may stub out apply without init_tool_approval; ignore.
        pass

REDACT_KEYS = {"api_key", "authorization", "token", "password", "file_text", "content"}


def _redact_value(key: str, value: Any) -> Any:
    if key in REDACT_KEYS:
        return "[REDACTED]"
    return value


def redact_arguments(args: dict[str, Any]) -> dict[str, Any]:
    return {k: _redact_value(k, v) for k, v in (args or {}).items()}


def approval_preset(preset: str) -> list[Any]:
    """Return preset approval policies for ci/dev/prod.

    - ci: approve all tools (no-op gate)
    - dev: approve most; escalate sensitive tools to a second policy that rejects
    - prod: terminate sensitive tools; approve others
    """
    from inspect_ai.approval._approval import Approval  # type: ignore
    try:
        from inspect_ai.approval._policy import ApprovalPolicy  # type: ignore
    except Exception:
        class ApprovalPolicy:  # type: ignore
            def __init__(self, approver, tools):
                self.approver = approver
                self.tools = tools
    from inspect_ai._util.registry import RegistryInfo, registry_tag  # type: ignore
    from inspect_ai.tool._tool_call import ToolCall  # type: ignore

    sensitive = re.compile(r"^(write_file|text_editor|bash|python|web_browser_)")

    async def approve_all(message, call: ToolCall, view, history):  # type: ignore
        return Approval(decision="approve")

    registry_tag(lambda: None, approve_all, RegistryInfo(type="approver", name="preset/approve_all"))

    async def dev_gate(message, call: ToolCall, view, history):  # type: ignore
        if sensitive.match(call.function):
            return Approval(decision="escalate", explanation="dev: escalate sensitive tool")
        return Approval(decision="approve")

    registry_tag(lambda: None, dev_gate, RegistryInfo(type="approver", name="preset/dev_gate"))

    async def reject_all(message, call: ToolCall, view, history):  # type: ignore
        return Approval(decision="reject", explanation="Rejected by policy")

    registry_tag(lambda: None, reject_all, RegistryInfo(type="approver", name="preset/reject_all"))

    async def prod_gate(message, call: ToolCall, view, history):  # type: ignore
        if sensitive.match(call.function):
            # include redacted args in explanation
            red = redact_arguments(call.arguments)
            return Approval(decision="terminate", explanation=json.dumps(red))
        return Approval(decision="approve")

    registry_tag(lambda: None, prod_gate, RegistryInfo(type="approver", name="preset/prod_gate"))

    match preset:
        case "ci":
            return [ApprovalPolicy(approver=approve_all, tools="*")]
        case "dev":
            return [
                ApprovalPolicy(approver=dev_gate, tools="*"),
                ApprovalPolicy(approver=reject_all, tools="*"),
            ]
        case "prod":
            return [ApprovalPolicy(approver=prod_gate, tools="*")]
        case _:
            raise ValueError(f"Unknown approval preset: {preset}")


__all__ = [
    "approval_from_interrupt_config",
    "activate_approval_policies",
    "approval_preset",
    "redact_arguments",
]

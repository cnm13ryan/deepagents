from __future__ import annotations

import json
import os
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
        info = RegistryInfo(type="approver", name=f"inline/{tool}")
        # Primary: attach registry info using Inspect's helper
        registry_tag(
            lambda: None,  # signature template without required args
            _approve,
            info,
        )
        # Fallback: also set the well-known attribute directly so environments
        # with partially stubbed approval modules still recognize the approver
        # Try multiple well-known attribute names used by Inspect versions
        for attr in ("__registry_info__", "REGISTRY_INFO"):
            try:
                setattr(_approve, attr, info)
            except Exception:
                pass

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
            # CI stays permissive for flexibility (call sites may layer exclusivity/kill-switch)
            return [ApprovalPolicy(approver=approve_all, tools="*")]
        case "dev":
            # Development: exclusivity/kill-switch first, then gates
            return approval_chain(
                [
                    ApprovalPolicy(approver=dev_gate, tools="*"),
                    ApprovalPolicy(approver=reject_all, tools="*"),
                ]
            )
        case "prod":
            # Production: exclusivity/kill-switch first, then termination gate
            return approval_chain([ApprovalPolicy(approver=prod_gate, tools="*")])
        case _:
            raise ValueError(f"Unknown approval preset: {preset}")


__all__ = [
    "approval_from_interrupt_config",
    "activate_approval_policies",
    "approval_preset",
    "redact_arguments",
    "handoff_exclusive_policy",
    "parallel_kill_switch_policy",
    "approval_chain",
]


def handoff_exclusive_policy() -> list[Any]:
    """Enforce first-handoff exclusivity within an assistant turn.

    If the most recent assistant message contains any handoff tool calls
    (function name prefix "transfer_to_"), then only the first such handoff
    is approved; all other tool calls from that same message are skipped.

    Skipped calls are rejected with explanation "Skipped due to handoff exclusivity"
    and a repo-local logger event is emitted via tools._log_tool_event with:
      {tool:"handoff_exclusive", phase:"skipped", selected_handoff_id, skipped_function}.
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

    def _get(obj: Any, name: str, default: Any = None) -> Any:
        try:
            return getattr(obj, name)
        except Exception:
            try:
                return obj.get(name, default)  # type: ignore[attr-defined]
            except Exception:
                return default

    def _last_assistant_with_calls(message: Any, history: list[Any]) -> Any | None:
        # Prefer the current message when it has tool_calls; otherwise scan history backwards
        tcs = _get(message, "tool_calls") if message is not None else None
        if isinstance(tcs, (list, tuple)) and len(tcs) > 0:
            return message
        for msg in reversed(list(history or [])):
            tcs = _get(msg, "tool_calls")
            if isinstance(tcs, (list, tuple)) and len(tcs) > 0:
                return msg
        return None

    def _first_handoff_from_message(msg: Any) -> ToolCall | None:  # type: ignore[valid-type]
        tool_calls = _get(msg, "tool_calls") or []
        for tc in tool_calls:
            fn = _get(tc, "function", "")
            if isinstance(fn, str) and fn.startswith("transfer_to_"):
                return tc  # type: ignore[return-value]
        return None

    async def approver(message, call: ToolCall, view, history):  # type: ignore[no-redef]
        # Identify the source assistant message for this batch of tool calls
        source = _last_assistant_with_calls(message, history)
        if source is None:
            # No batch context; allow subsequent presets/gates to decide
            return Approval(decision="escalate")

        selected = _first_handoff_from_message(source)
        if selected is None:
            # No handoff present: exclusivity not applicable; approve
            return Approval(decision="approve")

        selected_id = _get(selected, "id")
        current_is_handoff = isinstance(call.function, str) and call.function.startswith("transfer_to_")

        if current_is_handoff and call.id == selected_id:
            return Approval(decision="approve")

        # Skip everything else in the same batch when a handoff is present
        try:
            # Lazy import to avoid tools module at import time
            from .tools import _log_tool_event  # local import

            _log_tool_event(
                name="handoff_exclusive",
                phase="skipped",
                extra={
                    "selected_handoff_id": selected_id,
                    "skipped_function": call.function,
                },
            )
        except Exception:
            # Logging should never fail policy decisions
            pass

        # Emit a standardized transcript ToolEvent to reflect the skip
        # (kept separate from repo-local logger above for operator-facing parity).
        try:
            from inspect_ai.log._transcript import ToolEvent, transcript  # type: ignore
            from inspect_ai.tool._tool_call import ToolCallError  # type: ignore

            # Synthesize a minimal ToolEvent for the skipped call.
            # Note: we use ToolCallError type 'approval' to indicate policy enforcement
            # and include attribution details in `metadata`.
            ev = ToolEvent(
                id=str(call.id),
                function=str(call.function),
                arguments=dict(call.arguments or {}),
                pending=False,
                error=ToolCallError("approval", "Skipped due to handoff"),
                metadata={
                    "selected_handoff_id": selected_id,
                    "skipped_function": call.function,
                    "source": "policy/handoff_exclusive",
                },
            )
            transcript()._event(ev)
        except Exception:
            # Never block a decision on transcript emission
            pass

        return Approval(decision="reject", explanation="Skipped due to handoff exclusivity")

    # Tag for Inspect logging/registry
    registry_tag(lambda: None, approver, RegistryInfo(type="approver", name="policy/handoff_exclusive"))

    return [ApprovalPolicy(approver=approver, tools="*")]


def parallel_kill_switch_policy() -> list[Any]:
    """Global kill-switch to disable parallel tool execution for non-handoff tools.

    When either `INSPECT_TOOL_PARALLELISM_DISABLE` or `INSPECT_DISABLE_TOOL_PARALLEL`
    is truthy and the most recent assistant message contains more than one
    tool call, approve only the first non-handoff tool call and reject the rest.

    Notes:
    - Handoff tools (name starts with "transfer_to_") are handled by
      `handoff_exclusive_policy()` and are not gated here; if a handoff is present
      in the batch, this policy escalates so the exclusivity policy decides.
    - Truthy values: {"1", "true", "yes", "on"} (case-insensitive).
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

    def _truthy(val: str | None) -> bool:
        if val is None:
            return False
        return val.strip().lower() in {"1", "true", "yes", "on"}

    def _get(obj: Any, name: str, default: Any = None) -> Any:
        try:
            return getattr(obj, name)
        except Exception:
            try:
                return obj.get(name, default)  # type: ignore[attr-defined]
            except Exception:
                return default

    def _last_assistant_with_calls(message: Any, history: list[Any]) -> Any | None:
        tcs = _get(message, "tool_calls") if message is not None else None
        if isinstance(tcs, (list, tuple)) and len(tcs) > 0:
            return message
        for msg in reversed(list(history or [])):
            tcs = _get(msg, "tool_calls")
            if isinstance(tcs, (list, tuple)) and len(tcs) > 0:
                return msg
        return None

    def _first_handoff_from_message(msg: Any) -> ToolCall | None:  # type: ignore[valid-type]
        for tc in _get(msg, "tool_calls") or []:
            fn = _get(tc, "function", "")
            if isinstance(fn, str) and fn.startswith("transfer_to_"):
                return tc  # type: ignore[return-value]
        return None

    def _first_non_handoff_id(msg: Any) -> Any:
        for tc in _get(msg, "tool_calls") or []:
            fn = _get(tc, "function", "")
            if not (isinstance(fn, str) and fn.startswith("transfer_to_")):
                return _get(tc, "id")
        return None

    async def approver(message, call: ToolCall, view, history):  # type: ignore[no-redef]
        # Short-circuit unless kill-switch is enabled
        if not (_truthy(os.getenv("INSPECT_TOOL_PARALLELISM_DISABLE")) or _truthy(os.getenv("INSPECT_DISABLE_TOOL_PARALLEL"))):
            return Approval(decision="escalate")

        source = _last_assistant_with_calls(message, history)
        if source is None:
            return Approval(decision="escalate")

        tool_calls = _get(source, "tool_calls") or []
        if not isinstance(tool_calls, (list, tuple)) or len(tool_calls) <= 1:
            # Nothing parallel to gate
            return Approval(decision="escalate")

        # If a handoff exists in this batch, defer to exclusivity policy
        if _first_handoff_from_message(source) is not None:
            return Approval(decision="escalate")

        first_allowed = _first_non_handoff_id(source)
        if first_allowed is None:
            # Only handoffs present or unable to resolve; let other policies decide
            return Approval(decision="escalate")

        if call.id == first_allowed:
            return Approval(decision="approve")

        # Reject subsequent non-handoff tool calls in the same batch
        try:
            from .tools import _log_tool_event  # local import for logging

            _log_tool_event(
                name="parallel_kill_switch",
                phase="skipped",
                extra={
                    "first_allowed_id": first_allowed,
                    "skipped_function": call.function,
                },
            )
        except Exception:
            pass

        # Emit standardized transcript ToolEvent for the skip
        try:
            from inspect_ai.log._transcript import ToolEvent, transcript  # type: ignore
            from inspect_ai.tool._tool_call import ToolCallError  # type: ignore

            ev = ToolEvent(
                id=str(call.id),
                function=str(call.function),
                arguments=dict(call.arguments or {}),
                pending=False,
                error=ToolCallError("approval", "Parallel disabled: only first tool approved"),
                metadata={
                    "first_allowed_id": first_allowed,
                    "skipped_function": call.function,
                    "source": "policy/parallel_kill_switch",
                },
            )
            transcript()._event(ev)
        except Exception:
            pass

        return Approval(decision="reject", explanation="Parallel disabled: only first tool approved")

    registry_tag(lambda: None, approver, RegistryInfo(type="approver", name="policy/parallel_kill_switch"))

    return [ApprovalPolicy(approver=approver, tools="*")]


def approval_chain(
    *policies: Any,
    include_exclusivity: bool = True,
    include_kill_switch: bool = True,
) -> list[Any]:
    """Return a canonical, ordered policy chain with safe precedence.

    Precedence is guaranteed:
    1) Handoff exclusivity (if enabled)
    2) Parallel kill-switch (if enabled)
    3) Caller-provided policies in given order

    Notes
    - Each element in ``policies`` can be a single ``ApprovalPolicy`` or a
      ``list[ApprovalPolicy]``. Falsy entries are ignored.
    - This helper centralizes ordering to avoid accidental reordering at call sites.
    """

    chain: list[Any] = []
    if include_exclusivity:
        try:
            chain.extend(handoff_exclusive_policy())
        except Exception:
            pass
    if include_kill_switch:
        try:
            chain.extend(parallel_kill_switch_policy())
        except Exception:
            pass

    for p in policies:
        if not p:
            continue
        if isinstance(p, list):
            chain.extend(p)
        else:
            chain.append(p)
    return chain

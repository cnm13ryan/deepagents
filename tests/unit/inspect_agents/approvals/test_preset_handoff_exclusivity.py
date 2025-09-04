#!/usr/bin/env python3
"""Ensure dev/prod presets include handoff exclusivity.

Asserts that `approval_preset("dev"|"prod")` returns a policy list that
contains an approver tagged with registry name `policy/handoff_exclusive`, and
that `approval_preset("ci")` does not. Also sanity‑checks the approver’s
practical effect on a mixed handoff/non‑handoff batch.
"""

import asyncio
import sys
import types


def _install_minimal_stubs():
    # Stub approval._approval.Approval
    appr = types.ModuleType('inspect_ai.approval._approval')
    class Approval:  # pragma: no cover - tiny shim
        def __init__(self, decision, modified=None, explanation=None):
            self.decision = decision
            self.modified = modified
            self.explanation = explanation
    appr.Approval = Approval
    sys.modules['inspect_ai.approval._approval'] = appr

    # Stub approval._policy.ApprovalPolicy (constructor compatibility only)
    pol = types.ModuleType('inspect_ai.approval._policy')
    class ApprovalPolicy:  # pragma: no cover - tiny shim
        def __init__(self, approver, tools):
            self.approver = approver
            self.tools = tools
    pol.ApprovalPolicy = ApprovalPolicy
    sys.modules['inspect_ai.approval._policy'] = pol

    # Stub tool._tool_call.ToolCall
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

    # Stub registry so registry_tag attaches an attribute we can inspect
    reg = types.ModuleType('inspect_ai._util.registry')
    class RegistryInfo:  # pragma: no cover - tiny shim
        def __init__(self, type, name):
            self.type = type
            self.name = name
    def registry_tag(template, func, info):  # pragma: no cover - attach marker
        try:
            setattr(func, '__registry_info__', info)
        except Exception:
            pass
    reg.RegistryInfo = RegistryInfo
    reg.registry_tag = registry_tag
    sys.modules['inspect_ai._util.registry'] = reg


def _load_module_via_exec():
    # Load approval.py directly to avoid package side-effects
    g = {}
    with open('src/inspect_agents/approval.py', encoding='utf-8') as f:
        code = f.read()
    exec(code, g, g)
    return g


def _policy_names(policies):
    names = []
    for p in policies:
        info = getattr(p.approver, '__registry_info__', None)
        if info is not None:
            names.append(getattr(info, 'name', None))
    return [n for n in names if n]


def test_presets_include_exclusivity_marker(approval_modules_guard):
    _install_minimal_stubs()
    mod = _load_module_via_exec()

    dev_names = _policy_names(mod['approval_preset']('dev'))
    prod_names = _policy_names(mod['approval_preset']('prod'))
    ci_names = _policy_names(mod['approval_preset']('ci'))

    assert 'policy/handoff_exclusive' in dev_names
    assert 'policy/handoff_exclusive' in prod_names
    assert 'policy/handoff_exclusive' not in ci_names


def test_exclusivity_policy_effect_is_present_in_presets(approval_modules_guard):
    """Find the exclusivity approver in dev/prod and validate behavior.

    We call the approver directly (not via policy_approver) to isolate its
    semantics: first handoff approved; non‑handoff skipped with explanation.
    """
    _install_minimal_stubs()
    mod = _load_module_via_exec()

    def get_excl(policies):
        for p in policies:
            info = getattr(p.approver, '__registry_info__', None)
            if getattr(info, 'name', None) == 'policy/handoff_exclusive':
                return p.approver
        raise AssertionError('Exclusivity approver not found in presets')

    # Minimal message container
    class _Msg:
        def __init__(self, tool_calls):
            self.tool_calls = tool_calls

    # Build a mixed batch
    tool_call_cls = sys.modules['inspect_ai.tool._tool_call'].ToolCall
    handoff = tool_call_cls(id='1', function='transfer_to_researcher', arguments={})
    non_handoff = tool_call_cls(id='2', function='read_file', arguments={'file_path': 'README.md'})
    msg = _Msg([handoff, non_handoff])
    history = [msg]

    for preset in ('dev', 'prod'):
        exclusivity = get_excl(mod['approval_preset'](preset))
        # First handoff should approve
        res1 = asyncio.run(exclusivity(msg, handoff, None, history))
        assert getattr(res1, 'decision', None) == 'approve'
        # Non‑handoff should be rejected with exclusivity explanation
        res2 = asyncio.run(exclusivity(msg, non_handoff, None, history))
        assert getattr(res2, 'decision', None) == 'reject'
        assert 'exclusivity' in (getattr(res2, 'explanation', '') or '')

# Cleanup handled by approval_modules_guard fixture


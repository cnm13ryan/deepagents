# test(approvals): ensure exclusivity policy runs first in dev/prod

from __future__ import annotations

from typing import Any

from inspect_agents.approval import approval_preset


def _names(policies: list[Any]) -> list[str]:
    # Extract stable function names for approvers
    names: list[str] = []
    for p in policies:
        name = getattr(p.approver, "__name__", None)
        names.append(name if isinstance(name, str) else str(p.approver))
    return names


def test_preset_order_dev_prod_ci():
    dev = _names(approval_preset("dev"))
    prod = _names(approval_preset("prod"))
    ci = _names(approval_preset("ci"))

    # dev: exclusivity approver first
    assert dev[0] == "approver"
    # and dev-specific gates follow in order (allow extra policies between/after)
    assert "dev_gate" in dev[1:]
    assert "reject_all" in dev[1:]
    assert dev.index("dev_gate") < dev.index("reject_all")

    # prod: exclusivity approver first, then prod termination gate (allow extras after)
    assert prod[0] == "approver"
    assert "prod_gate" in prod[1:]

    # ci: unchanged permissive approve-all
    assert ci == ["approve_all"]


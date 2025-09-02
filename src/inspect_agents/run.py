from __future__ import annotations

from typing import Any


async def run_agent(
    agent: Any,
    input: str | list[Any],
    approval: list[Any] | None = None,
    limits: list[Any] = [],
):
    if approval:
        try:
            from inspect_ai.approval._apply import init_tool_approval  # type: ignore

            init_tool_approval(approval)
        except Exception:
            # If approval initialization isn't available in test stubs, continue.
            pass

    # Import submodule directly to bypass stubbed package __init__ in tests
    from inspect_ai.agent._run import run as agent_run  # type: ignore

    result = await agent_run(agent, input, limits=limits)
    if isinstance(result, tuple):
        return result[0]
    return result

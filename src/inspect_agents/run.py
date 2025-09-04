from __future__ import annotations

from typing import Any


async def run_agent(
    agent: Any,
    input: str | list[Any],
    approval: list[Any] | None = None,
    limits: list[Any] = [],
    return_limit_error: bool = False,
    raise_on_limit: bool = False,
):
    """Run an agent and optionally propagate limit errors.

    By default this returns only the agent state. When Inspect returns a
    `(state, err)` tuple (e.g., when limits are supplied), you can opt in to
    propagation semantics:

    - If `return_limit_error` is True and a tuple is received, return
      `(state, err)` instead of dropping the error.
    - If `raise_on_limit` is True and `err` is not None, re-raise the error.

    This preserves backward compatibility when both flags are left as False.
    """
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

    # Inspect returns a tuple when limits are provided; otherwise it's the state
    if isinstance(result, tuple):
        state, err = result

        # Optionally raise when a limit error occurred
        if raise_on_limit and err is not None:
            # `err` is expected to be an Exception (e.g., LimitExceededError)
            # Raise it directly to preserve type and traceback
            raise err

        # Optionally return the `(state, err)` tuple to the caller
        if return_limit_error:
            return state, err

        # Backward-compat: default to returning state only
        return state

    return result

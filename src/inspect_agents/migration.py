from __future__ import annotations

from typing import Any, Sequence


def _resolve_builtin_tools(names: list[str] | None) -> list[object]:
    from inspect_agents import tools as builtin

    name_to_ctor = {
        "write_todos": builtin.write_todos,
        "write_file": builtin.write_file,
        "read_file": builtin.read_file,
        "ls": builtin.ls,
        "edit_file": builtin.edit_file,
    }

    selected = list(name_to_ctor.keys()) if names is None else names
    return [name_to_ctor[n]() for n in selected if n in name_to_ctor]


def create_deep_agent(
    tools: Sequence[object] | None,
    instructions: str,
    *,
    model: Any | None = None,
    subagents: list[dict[str, Any]] | None = None,
    state_schema: Any | None = None,
    builtin_tools: list[str] | None = None,
    interrupt_config: dict[str, Any] | None = None,
    attempts: int = 1,
    truncation: str = "disabled",
) -> object:
    """Drop-in deepagents-style constructor backed by Inspect.

    Maps the familiar deepagents surface to Inspect's ReAct agent, sub-agents,
    and optional approval policies. Unused params are accepted for parity.
    """
    from inspect_ai.agent._react import react
    from inspect_agents.agents import BASE_PROMPT, build_subagents

    # Resolve built-ins and optional sub-agents
    base_tools = _resolve_builtin_tools(builtin_tools)
    extra_tools = list(tools or [])

    if subagents:
        extra_tools.extend(build_subagents(subagents, base_tools))

    # Build top-level ReAct supervisor
    full_prompt = (instructions or "").rstrip() + "\n\n" + BASE_PROMPT
    agent = react(
        prompt=full_prompt,
        tools=base_tools + extra_tools,
        model=model,
        attempts=attempts,
        submit=True,
        truncation=truncation,  # default: disabled
    )

    # If interrupts provided, convert to approval policies and wrap to init on call
    if interrupt_config:
        from inspect_ai.agent._agent import agent as as_agent
        from inspect_agents.approval import (
            approval_from_interrupt_config,
            activate_approval_policies,
        )

        policies = approval_from_interrupt_config(interrupt_config)

        @as_agent
        def with_approvals():
            async def execute(state):
                activate_approval_policies(policies)
                return await agent(state)

            return execute

        return with_approvals

    return agent


__all__ = ["create_deep_agent"]


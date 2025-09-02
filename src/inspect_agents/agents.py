from __future__ import annotations

"""Supervisor agent (Inspect ReAct) for deepagents rewrite.

Provides `build_supervisor()` which returns an Inspect `react` agent configured
with a base prompt and built-in tools (todos + virtual FS). The agent terminates
via the default `submit()` tool provided by Inspect.
"""

from typing import Sequence, TypedDict, NotRequired, Any


# Base prompt modeled after deepagents.base_prompt
BASE_PROMPT = (
    "You have access to a number of standard tools\n\n"
    "## `write_todos`\n\n"
    "You have access to the `write_todos` tools to help you manage and plan tasks."
    " Use these tools VERY frequently to ensure that you are tracking your tasks and"
    " giving the user visibility into your progress.\n"
    "These tools are also EXTREMELY helpful for planning tasks, and for breaking down"
    " larger complex tasks into smaller steps. If you do not use this tool when"
    " planning, you may forget to do important tasks - and that is unacceptable.\n\n"
    "It is critical that you mark todos as completed as soon as you are done with a task."
    " Do not batch up multiple tasks before marking them as completed.\n"
)


def _built_in_tools():
    # Local imports to avoid importing inspect_ai at module import time
    from inspect_agents.tools import (
        write_todos,
        write_file,
        read_file,
        ls,
        edit_file,
        standard_tools,
    )

    base = [write_todos(), write_file(), read_file(), ls(), edit_file()]
    # Append optional standard tools (enabled via env flags)
    return base + standard_tools()


def build_supervisor(
    prompt: str,
    tools: Sequence[object] | None = None,
    *,
    attempts: int = 1,
    model: object | None = None,
    truncation: str = "disabled",
):
    """Create a top-level ReAct supervisor agent.

    Args:
        prompt: Base instructions to prepend before standard guidance.
        tools: Additional Tools/ToolDefs/ToolSources to provide.
        attempts: Max attempts for submit-terminated loop.
        model: Optional Inspect model (string/Model/Agent). If None, uses default.
        truncation: Overflow policy for long conversations ("disabled" or "auto").

    Returns:
        Inspect `Agent` compatible with react() (submit-enabled).
    """
    from inspect_ai.agent._react import react

    full_prompt = (prompt or "").rstrip() + "\n\n" + BASE_PROMPT

    tools = list(tools or [])
    tools = _built_in_tools() + tools

    return react(
        prompt=full_prompt,
        tools=tools,
        model=model,
        attempts=attempts,
        submit=True,
        truncation=truncation,  # pass-through; no custom limits for now
    )


class SubAgentCfg(TypedDict):
    name: str
    description: str
    prompt: str
    tools: NotRequired[list[str]]
    model: NotRequired[Any]
    mode: NotRequired[str]  # "handoff" (default) or "tool"
    input_filter: NotRequired[Any]
    output_filter: NotRequired[Any]
    limits: NotRequired[list[Any]]


def build_subagents(
    configs: list[SubAgentCfg], base_tools: list[object]
) -> list[object]:
    """Create handoff/as_tool wrappers for configured sub-agents.

    - Each config produces an Inspect agent via `react(...)` with the provided
      prompt, description, and tools (subset of `base_tools` if `tools` is set).
    - Returns tools named `transfer_to_<name>` (handoff) or the agent as a
      single-shot tool when `mode == 'tool'`.
    """
    from inspect_ai.agent._react import react
    from inspect_ai.agent._handoff import handoff
    from inspect_ai.agent._as_tool import as_tool

    # Map base tools by name for per-agent selection
    tool_by_name: dict[str, object] = {}
    try:
        from inspect_ai.tool._tool_def import ToolDef
        from inspect_ai.tool._tool import Tool
        for t in base_tools:
            tdef = ToolDef(t) if not isinstance(t, ToolDef) else t
            tool_by_name[tdef.name] = t
    except Exception:
        # Fallback best-effort by object repr if ToolDef unavailable
        for t in base_tools:
            tool_by_name[getattr(t, "__name__", repr(t))] = t

    out: list[object] = []
    for cfg in configs:
        name = cfg["name"]
        desc = cfg["description"]
        prompt = cfg["prompt"]
        mode = cfg.get("mode", "handoff")

        # Resolve tools subset in config (by name) or use all base_tools
        selected_tools: list[object]
        if "tools" in cfg:
            selected_tools = [tool_by_name[n] for n in cfg["tools"] if n in tool_by_name]
        else:
            selected_tools = list(base_tools)

        # Build the sub-agent
        agent = react(
            name=name,
            description=desc,
            prompt=prompt,
            tools=selected_tools,
            model=cfg.get("model"),
            submit=True,
        )

        # Wrap as requested
        if mode == "tool":
            out.append(as_tool(agent, description=desc))
        else:
            out.append(
                handoff(
                    agent,
                    description=desc,
                    input_filter=cfg.get("input_filter"),
                    output_filter=cfg.get("output_filter"),
                    tool_name=f"transfer_to_{name}",
                    limits=cfg.get("limits", []),
                )
            )

    return out

from __future__ import annotations

"""Supervisor agent (Inspect ReAct) for deepagents rewrite.

Provides `build_supervisor()` which returns an Inspect `react` agent configured
with a base prompt and built-in tools (todos + virtual FS). The agent terminates
via the default `submit()` tool provided by Inspect.
"""

from typing import Sequence, TypedDict, NotRequired, Any


# Base prompt modeled after deepagents.base_prompt
BASE_PROMPT_HEADER = (
    "You have access to a number of tools.\n\n"
)

BASE_PROMPT_TODOS = (
    "## Todo & Filesystem Tools\n\n"
    "- `write_todos`: Update and track your plan frequently.\n"
    "- `ls`, `read_file`, `write_file`, `edit_file`: Operate on a virtual in‑memory FS by default.\n"
    "  In sandbox mode, these map to a safe host text editor.\n\n"
    "Mark todos complete as soon as a task is finished (don’t batch).\n"
)

# Backcompat constant for migration shim
BASE_PROMPT = BASE_PROMPT_HEADER + BASE_PROMPT_TODOS

def _format_standard_tools_section(all_tools: list[object]) -> str:
    """Return a short section enumerating available Inspect standard tools.

    Groups standard tools separately so the model understands additional
    capabilities beyond the Todo/FS utilities.
    """
    try:
        from inspect_ai.tool._tool_def import ToolDef
    except Exception:
        # If ToolDef is unavailable (e.g., in stubs), skip annotation
        return ""

    names = set()
    for t in all_tools:
        try:
            tdef = ToolDef(t) if not isinstance(t, ToolDef) else t
            names.add(tdef.name)
        except Exception:
            pass

    std_names: list[str] = []
    # Detect presence of representative tools
    if "think" in names:
        std_names.append("think")
    if "web_search" in names:
        std_names.append("web_search")
    if "bash" in names:
        std_names.append("bash")
    if "python" in names:
        std_names.append("python")
    # Web browser exposes multiple tool names; detect by go
    browser_present = any(n.startswith("web_browser_") for n in names)
    if browser_present:
        std_names.append("web_browser")
    if "text_editor" in names:
        std_names.append("text_editor")

    if not std_names:
        return ""

    std_list = ", ".join(std_names)
    return (
        "\n## Standard Tools\n\n"
        f"Additional standard tools are enabled: {std_list}.\n"
        "Use `web_search` to retrieve up‑to‑date information from the web when needed."
        " Prefer citing sources in your answer.\n"
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

    # Compose prompt with clear tool sections (Todo/FS + Standard)
    tools = list(tools or [])
    builtins = _built_in_tools()
    tools = builtins + tools

    full_prompt = (
        (prompt or "").rstrip()
        + "\n\n"
        + BASE_PROMPT_HEADER
        + BASE_PROMPT_TODOS
        + _format_standard_tools_section(builtins)
    )

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
    # Default quarantine filters and env toggles
    from inspect_agents.filters import (
        default_input_filter,
        default_output_filter,
        should_inherit_filters,
    )

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
            # Resolve filters: per-config wins; otherwise env-driven defaults
            inherit = should_inherit_filters()
            input_filter = cfg.get("input_filter") if "input_filter" in cfg else (default_input_filter() if inherit else None)
            output_filter = cfg.get("output_filter") if "output_filter" in cfg else default_output_filter()

            out.append(
                handoff(
                    agent,
                    description=desc,
                    input_filter=input_filter,
                    output_filter=output_filter,
                    tool_name=f"transfer_to_{name}",
                    limits=cfg.get("limits", []),
                )
            )

    return out

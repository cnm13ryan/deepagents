#!/usr/bin/env python3
"""
Inspect task wrapper for the research composition (so `inspect eval` works here).

Usage
- uv run inspect eval examples/research/task.py \
  -T prompt="Curate a list of arXiv papers that Quantinuum published in 2025"

Options
- -T config="examples/research/inspect.yaml"  # load YAML composition
- -T enable_web_search=true                   # enable standard web_search tool

Environment
- INSPECT_ENABLE_WEB_SEARCH=1 TAVILY_API_KEY=... (or GOOGLE_CSE_* keys)
"""

from __future__ import annotations

import os

from inspect_ai import Task, task
from inspect_ai.dataset import Sample

from inspect_agents.agents import build_subagents, build_supervisor
from inspect_agents.config import load_and_build
from inspect_agents.model import resolve_model
from inspect_agents.tools import (
    edit_file,
    ls,
    read_file,
    standard_tools,
    update_todo_status,
    write_file,
    write_todos,
)


@task
def research_task(
    prompt: str = "Write a short overview of Inspect‑AI",
    attempts: int = 1,
    config: str | None = None,
    enable_web_search: bool = False,
):
    """Expose the research composition as an Inspect task.

    Mirrors the composition used by `examples/research/run_local.py`.
    Pass `config` to load a YAML composition; otherwise use the inline default.
    """

    # Optional tool toggle via task parameter (mirrors env behavior)
    if enable_web_search:
        os.environ["INSPECT_ENABLE_WEB_SEARCH"] = "1"

    model_id = resolve_model()

    if config:
        # Build from YAML (returns: agent, tools, approvals)
        agent, _, _ = load_and_build(config, model=model_id)
    else:
        # Build base tools and sub-agents inline (same as the local runner)
        builtins = [write_todos(), update_todo_status(), write_file(), read_file(), ls(), edit_file()]
        base_tools = builtins + standard_tools()

        sub_research_prompt = (
            "You are a dedicated researcher. Your job is to conduct research based on the user's question.\n\n"
            "Conduct thorough research and then reply with a detailed answer."
        )
        sub_critique_prompt = (
            "You are a dedicated editor tasked to critique a report.\n\n"
            "The report is in `final_report.md`; the question is in `question.txt`.\n"
            "Respond with a detailed critique and concrete improvements."
        )

        sub_configs = [
            {
                "name": "research-agent",
                "description": (
                    "Used to research more in-depth questions. Only give this researcher one topic at a time."
                ),
                "prompt": sub_research_prompt,
                "tools": ["web_search", "read_file", "write_file", "ls"],
                "mode": "handoff",
            },
            {
                "name": "critique-agent",
                "description": "Used to critique the final report.",
                "prompt": sub_critique_prompt,
                "tools": ["web_search", "read_file", "write_file", "ls"],
                "mode": "handoff",
            },
        ]

        subagent_tools = build_subagents(configs=sub_configs, base_tools=base_tools)

        agent = build_supervisor(
            prompt="You are a helpful researcher.",
            tools=subagent_tools,
            attempts=attempts,
            model=model_id,
        )

    return Task(
        dataset=[Sample(input=prompt)],
        solver=agent,
    )


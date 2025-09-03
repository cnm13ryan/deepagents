"""
Ad-hoc prompt task for Inspect CLI.

Run with:

  uv run inspect eval examples/inspect/prompt_task.py -T prompt="Write a concise overview of LangGraph"

Standard tools can be toggled at runtime via env, for example:

  INSPECT_ENABLE_THINK=1 \
  INSPECT_ENABLE_WEB_SEARCH=1 \
  TAVILY_API_KEY=... \
  uv run inspect eval examples/inspect/prompt_task.py -T prompt="..."

The Inspect CLI will automatically load `.env` in the current directory (and
parents). Run from the repo root to pick up your `.env`, or export vars in
your shell before invoking.
"""

from inspect_ai import Task, task
from inspect_ai.agent import react
from inspect_ai.dataset import Sample

from inspect_agents.model import resolve_model
from inspect_agents.tools import (
    edit_file,
    ls,
    read_file,
    standard_tools,
    write_file,
    write_todos,
)


@task
def prompt_task(
    prompt: str = "Find the latest publication from Quantinuum in arxiv",
    attempts: int = 1,
):
    """Single-sample prompt task using Inspect agents + tools."""
    tools = [write_todos(), write_file(), read_file(), ls(), edit_file()] + standard_tools()
    return Task(
        dataset=[Sample(input=prompt)],
        solver=react(
            prompt="",
            tools=tools,
            attempts=attempts,
            submit=True,
            model=resolve_model(),
        ),
    )

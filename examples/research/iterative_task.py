"""
Inspect task: Iterative Agent (no submit) — runs via `inspect eval`.

Usage
- uv run inspect eval examples/research/iterative_task.py \
    -T prompt="List files and propose a small refactor plan" \
    -T time_limit=300 -T max_steps=30 -T enable_exec=true

Notes
- Optional tools are env-gated:
  - enable exec:   set -T enable_exec=true (sets INSPECT_ENABLE_EXEC=1)
  - enable search: export INSPECT_ENABLE_WEB_SEARCH=1 and provider keys; or use
    repo examples that expose a research composition with web_search tools.
"""

from __future__ import annotations

import os

from inspect_ai import Task, task
from inspect_ai.dataset import Sample

from inspect_agents import build_iterative_agent
from inspect_agents.model import resolve_model


@task
def iterative_task(
    prompt: str = "List repository files and summarize key modules.",
    time_limit: int = 600,
    max_steps: int = 40,
    enable_exec: bool = False,
):
    """Expose the Iterative Agent as an Inspect task (no submit semantics)."""

    if enable_exec:
        os.environ["INSPECT_ENABLE_EXEC"] = "1"

    agent = build_iterative_agent(
        prompt=(
            "You are an iterative coding agent. Work in small, verifiable steps. "
            "Use tools when needed and keep the repo tidy."
        ),
        model=resolve_model(),
        real_time_limit_sec=int(time_limit),
        max_steps=int(max_steps),
    )

    return Task(
        dataset=[Sample(input=prompt)],
        solver=agent,
    )


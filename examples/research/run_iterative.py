#!/usr/bin/env python3
"""
Run the deepagents Iterative Agent (no submit): small, time/step‑bounded steps.

Examples
- Minimal:  uv run python examples/research/run_iterative.py "List repo files and summarize"
- With exec: INSPECT_ENABLE_EXEC=1 \
             uv run python examples/research/run_iterative.py --time-limit 300 --max-steps 20 \
               "Create docs/OUTLINE.md and add 3 sections"

Environment
- Model routing prefers local by default (Ollama). To change provider/model, set env
  as described in docs/reference/environment.md.
- Optional tools via env flags (see docs/tools/*):
  - INSPECT_ENABLE_EXEC=1          # enable bash() and python() tools
  - INSPECT_ENABLE_WEB_SEARCH=1    # enable web_search (requires API keys)
  - INSPECT_ENABLE_WEB_BROWSER=1   # enable browser tools
"""

from __future__ import annotations

import argparse
import asyncio
import os
from typing import Any

from inspect_agents.agents import build_iterative_agent
from inspect_agents.model import resolve_model
from inspect_agents.run import run_agent


async def _main() -> int:
    parser = argparse.ArgumentParser(description="Run the Iterative Agent (no submit).")
    parser.add_argument("prompt", nargs="*", help="User prompt text (default from $PROMPT)")
    parser.add_argument("--time-limit", type=int, default=600, help="Real-time limit in seconds (default 600)")
    parser.add_argument("--max-steps", type=int, default=40, help="Max loop steps (default 40)")
    parser.add_argument("--enable-exec", action="store_true", help="Enable bash/python tools via env flag")
    args = parser.parse_args()

    user_input = " ".join(args.prompt).strip() or os.getenv(
        "PROMPT", "List repository files and propose a small refactor plan."
    )

    if args.enable_exec:
        os.environ["INSPECT_ENABLE_EXEC"] = "1"

    # Resolve model (prefers local Ollama by default; see docs for env overrides)
    model_id = resolve_model()

    agent = build_iterative_agent(
        prompt=(
            "You are an iterative coding agent. Work in small, verifiable steps. "
            "Use tools when needed and keep the repo tidy."
        ),
        model=model_id,
        real_time_limit_sec=args.time_limit,
        max_steps=args.max_steps,
    )

    state = await run_agent(agent, user_input)

    # Best-effort: print completion or last assistant text
    text: str | None = getattr(state.output, "completion", None)
    if not text:
        try:
            text = state.output.choices[-1].message.text  # type: ignore[attr-defined]
        except Exception:
            text = None
    print(text or "[No assistant text]")
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_main()))


if __name__ == "__main__":
    main()

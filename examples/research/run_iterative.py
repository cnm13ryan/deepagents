#!/usr/bin/env python3
"""
Run the deepagents Iterative Agent (no submit): small, time/step‑bounded steps.

Examples
- Minimal:  uv run python examples/research/run_iterative.py "List repo files and summarize"
- With exec: INSPECT_ENABLE_EXEC=1 \
             uv run python examples/research/run_iterative.py --time-limit 300 --max-steps 20 \
               "Create docs/OUTLINE.md and add 3 sections"

Environment
- Model routing prefers local by default (Ollama). To change provider/model, use
  CLI flags `--provider/--model` or set env as described in
  docs/reference/environment.md.
- Optional tools via env flags (see docs/tools/*):
  - INSPECT_ENABLE_EXEC=1          # enable bash() and python() tools
  - INSPECT_ENABLE_WEB_SEARCH=1    # enable web_search (requires API keys)
  - INSPECT_ENABLE_WEB_BROWSER=1   # enable browser tools
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Ensure local repo sources are imported (not an installed wheel)
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

"""Imports moved into functions to satisfy E402 (imports at top).

Ruff flagged module-level imports occurring after path mutation. To keep
local import behavior (prefer repo `src/` over installed wheel) and satisfy
linting, import runtime dependencies inside `_main()`.
"""


def _load_env_files() -> None:
    """Load .env files from repo root and this example if available.

    Respects INSPECT_ENV_FILE and does not override pre-existing env vars.
    """
    try:
        from dotenv import load_dotenv  # type: ignore

        # 0) Explicit file via env var wins (highest precedence among files)
        explicit = os.getenv("INSPECT_ENV_FILE")
        if explicit:
            load_dotenv(explicit, override=False)

        # 1) Repo root .env
        load_dotenv(REPO_ROOT / ".env", override=False)

        # 2) Per-example .env (kept for convenience)
        load_dotenv(Path(__file__).parent / ".env", override=False)

        # 3) Centralized template as fill‑in (lowest precedence)
        load_dotenv(REPO_ROOT / "env_templates" / "inspect.env", override=False)
        return
    except Exception:
        pass


async def _main() -> int:
    # Local imports to ensure src/ precedence without violating E402
    from inspect_agents.agents import build_iterative_agent
    from inspect_agents.model import resolve_model
    from inspect_agents.run import run_agent
    parser = argparse.ArgumentParser(description="Run the Iterative Agent (no submit).")
    parser.add_argument("prompt", nargs="*", help="User prompt text (default from $PROMPT)")
    parser.add_argument("--time-limit", type=int, default=600, help="Real-time limit in seconds (default 600)")
    parser.add_argument("--max-steps", type=int, default=40, help="Max loop steps (default 40)")
    parser.add_argument("--enable-exec", action="store_true", help="Enable bash/python tools via env flag")
    parser.add_argument("--provider", default=os.getenv("DEEPAGENTS_MODEL_PROVIDER", "ollama"), help="Model provider (ollama, lm-studio, openai, ...)")
    parser.add_argument(
        "--model",
        default=os.getenv("INSPECT_EVAL_MODEL"),
        help="Explicit model name (optional; provider prefix allowed)",
    )
    args = parser.parse_args()

    user_input = " ".join(args.prompt).strip() or os.getenv(
        "PROMPT", "List repository files and propose a small refactor plan."
    )

    if args.enable_exec:
        os.environ["INSPECT_ENABLE_EXEC"] = "1"

    # Resolve model (prefers local Ollama by default; CLI/env may override)
    model_id = resolve_model(provider=args.provider, model=args.model)
    # Test hook: short-circuit and echo resolved model for subprocess tests
    if os.getenv("DEEPAGENTS_TEST_ECHO_MODEL") == "1":
        print(model_id)
        return 0

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
    _load_env_files()
    raise SystemExit(asyncio.run(_main()))


if __name__ == "__main__":
    main()

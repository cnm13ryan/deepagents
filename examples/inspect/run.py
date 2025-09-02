#!/usr/bin/env python3
"""
Run the Inspect‑AI path (inspect_agents) from the repo.

Features
- Loads .env from repo root and examples/inspect (if present)
- Resolves model via inspect_agents (defaults to LM‑Studio or env)
- Runs a minimal supervisor and prints the final completion
- Writes a transcript JSONL and prints its path

Usage
  uv run python examples/inspect/run.py "Write a short overview of LangGraph"

Environment
- DEEPAGENTS_MODEL_PROVIDER=ollama|lm-studio|openai|...
- LM_STUDIO_BASE_URL, LM_STUDIO_MODEL_NAME, LM_STUDIO_API_KEY (for LM‑Studio)
- OLLAMA_MODEL_NAME, OLLAMA_BASE_URL/OLLAMA_HOST (for Ollama)
- PROMPT (optional default prompt)
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def _load_env_files() -> None:
    """Load .env files from repo root and examples/inspect if available.

    Does not override pre-existing environment variables.
    """
    try:
        from dotenv import load_dotenv  # type: ignore

        # 0) Explicit file via env var wins (highest precedence among files)
        explicit = os.getenv("INSPECT_ENV_FILE")
        if explicit:
            load_dotenv(explicit, override=False)

        # 1) Repo root .env (typical project defaults)
        load_dotenv(REPO_ROOT / ".env", override=False)

        # 2) Legacy per-example .env (kept for back-compat)
        load_dotenv(Path(__file__).parent / ".env", override=False)

        # 3) Centralized templates as fill-ins (lowest precedence)
        load_dotenv(REPO_ROOT / "env_templates" / "inspect.env", override=False)
        return
    except Exception:
        pass

    # Minimal fallback parser
    def _load_one(path: Path) -> None:
        if not path.exists():
            return
        try:
            for raw in path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
        except Exception:
            # Best-effort only
            return

    _load_one(REPO_ROOT / ".env")
    _load_one(Path(__file__).parent / ".env")


async def _main() -> int:
    from inspect_agents.agents import build_supervisor
    from inspect_agents.logging import write_transcript
    from inspect_agents.model import resolve_model
    from inspect_agents.run import run_agent

    parser = argparse.ArgumentParser(description="Run the Inspect Agents supervisor.")
    parser.add_argument("prompt", nargs="*", help="User prompt text")
    parser.add_argument(
        "--provider",
        default=os.getenv("DEEPAGENTS_MODEL_PROVIDER", "lm-studio"),
        help="Model provider (ollama, lm-studio, openai, ...)",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("INSPECT_EVAL_MODEL"),
        help="Explicit model name (optional; provider prefix allowed)",
    )
    # Optional standard tool toggles (map to env for simplicity)
    parser.add_argument("--enable-think", action="store_true", help="Enable think() tool")
    parser.add_argument(
        "--enable-web-search",
        action="store_true",
        help=(
            "Enable web_search() tool (requires Tavily or Google CSE keys)"
        ),
    )
    parser.add_argument(
        "--enable-exec",
        action="store_true",
        help=(
            "Enable bash() and python() tools (requires sandbox)"
        ),
    )
    parser.add_argument(
        "--enable-web-browser",
        action="store_true",
        help=(
            "Enable web_browser() tools (requires sandbox + Playwright)"
        ),
    )
    parser.add_argument(
        "--enable-text-editor-tool",
        action="store_true",
        help=(
            "Expose text_editor() directly (optional; FS tools already "
            "route to it in sandbox mode)"
        ),
    )
    args = parser.parse_args()

    user_input = " ".join(args.prompt).strip() or os.getenv(
        "PROMPT", "Write a short overview of LangGraph"
    )

    # Reflect flags into env before building agent
    if args.enable_think:
        os.environ["INSPECT_ENABLE_THINK"] = "1"
    if args.enable_web_search:
        os.environ["INSPECT_ENABLE_WEB_SEARCH"] = "1"
    if args.enable_exec:
        os.environ["INSPECT_ENABLE_EXEC"] = "1"
    if args.enable_web_browser:
        os.environ["INSPECT_ENABLE_WEB_BROWSER"] = "1"
    if args.enable_text_editor_tool:
        os.environ["INSPECT_ENABLE_TEXT_EDITOR_TOOL"] = "1"

    model_id = resolve_model(provider=args.provider, model=args.model)
    agent = build_supervisor(prompt="You are helpful.", tools=[], attempts=1, model=model_id)
    result = await run_agent(agent, user_input)

    # Print the final assistant completion and transcript log path
    completion = getattr(result.output, "completion", None)
    print(completion or "[No completion]")
    print("Transcript:", write_transcript())
    return 0


def main() -> None:
    # Allow a lightweight pre-parse of --env-file to point at a specific env
    try:
        mini = argparse.ArgumentParser(add_help=False)
        mini.add_argument("--env-file")
        known, _ = mini.parse_known_args()
        if known.env_file:
            os.environ["INSPECT_ENV_FILE"] = known.env_file
    except Exception:
        pass

    _load_env_files()
    raise SystemExit(asyncio.run(_main()))


if __name__ == "__main__":
    main()

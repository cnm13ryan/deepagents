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
import os
import sys
import asyncio
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

        load_dotenv(REPO_ROOT / ".env", override=False)
        load_dotenv(Path(__file__).parent / ".env", override=False)
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
    from inspect_agents.model import resolve_model
    from inspect_agents.agents import build_supervisor
    from inspect_agents.run import run_agent
    from inspect_agents.logging import write_transcript

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
    args = parser.parse_args()

    user_input = " ".join(args.prompt).strip() or os.getenv(
        "PROMPT", "Write a short overview of LangGraph"
    )

    model_id = resolve_model(provider=args.provider, model=args.model)
    agent = build_supervisor(prompt="You are helpful.", tools=[], attempts=1, model=model_id)
    result = await run_agent(agent, user_input)

    # Print the final assistant completion and transcript log path
    completion = getattr(result.output, "completion", None)
    print(completion or "[No completion]")
    print("Transcript:", write_transcript())
    return 0


def main() -> None:
    _load_env_files()
    raise SystemExit(asyncio.run(_main()))


if __name__ == "__main__":
    main()


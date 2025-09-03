#!/usr/bin/env python3
# ruff: noqa: E402
"""
Inspect‑AI runner for the research example (no external agent frameworks).

What it does
- Loads .env files (repo root, this folder, or --env-file) without overriding
  existing env vars.
- Resolves a local‑first model via inspect_agents and runs a minimal supervisor
  once with the provided prompt.
- Prints the final completion and writes a transcript JSONL path.

Usage
  uv run python examples/research/run_local.py "What is Inspect‑AI?"
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

    # Minimal fallback parser if python-dotenv isn't available
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
            return

    _load_one(REPO_ROOT / ".env")
    _load_one(Path(__file__).parent / ".env")


async def _main() -> int:
    from inspect_agents.agents import build_supervisor, build_subagents
    from inspect_agents.logging import write_transcript
    from inspect_agents.model import resolve_model
    from inspect_agents.run import run_agent
    from inspect_agents.approval import approval_preset, handoff_exclusive_policy
    from inspect_agents.config import load_and_build
    from inspect_agents.tools import (
        edit_file,
        ls,
        read_file,
        standard_tools,
        update_todo_status,
        write_file,
        write_todos,
    )

    parser = argparse.ArgumentParser(
        description="Run the Inspect‑AI research supervisor.",
        epilog=(
            "Quarantine: control handoff input filtering via INSPECT_QUARANTINE_MODE "
            "(strict|scoped|off) and INSPECT_QUARANTINE_INHERIT=0/1."
        ),
    )
    parser.add_argument("prompt", nargs="*", help="User prompt text")
    parser.add_argument(
        "--enable-web-search",
        action="store_true",
        help="Enable Inspect standard web_search tool",
    )
    parser.add_argument(
        "--approval",
        choices=["dev", "ci", "prod"],
        help="Apply an approvals preset (dev|ci|prod)",
    )
    parser.add_argument(
        "--config",
        help="Load composition from YAML (inspect_agents.config)",
    )
    args = parser.parse_args()

    user_input = " ".join(args.prompt).strip() or os.getenv(
        "PROMPT", "Write a short overview of Inspect‑AI"
    )
    if args.enable_web_search:
        os.environ["INSPECT_ENABLE_WEB_SEARCH"] = "1"

    # Local‑first: let resolver choose provider/model (defaults to Ollama if unset)
    model_id = resolve_model()

    # If a YAML config is provided, build from config; else use the inline composition
    yaml_agent = None
    yaml_approvals = []
    if args.config:
        yaml_agent, _, yaml_approvals = load_and_build(args.config, model=model_id)
        agent = yaml_agent
    else:
        # Build base tools for sub-agents (same composition as library built-ins)
        builtins = [write_todos(), update_todo_status(), write_file(), read_file(), ls(), edit_file()]
        base_tools = builtins + standard_tools()

        # Sub-agent prompts (lightweight researcher and critique roles)
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
            attempts=1,
            model=model_id,
        )
    # Approval policies (optional): apply preset and handoff exclusivity in dev/prod
    policies = list(yaml_approvals or []) or None
    if args.approval:
        extra = list(approval_preset(args.approval))
        if args.approval in {"dev", "prod"}:
            extra.extend(handoff_exclusive_policy())
        policies = (policies or []) + extra
    result = await run_agent(agent, user_input, approval=policies)

    # Print the final assistant completion and transcript log path
    completion = getattr(result.output, "completion", None)
    print(completion or "[No completion]")
    print("Transcript:", write_transcript())
    return 0


def main() -> None:
    # Optional lightweight pre-parse of --env-file to point at a specific env
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

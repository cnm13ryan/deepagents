#!/usr/bin/env python
"""
Local runner for the Deep Research agent using constituent components from this repo.

Why: Avoid importing an installed `deepagents` wheel from PyPI. This script injects the
repo's `src/` into `sys.path` so imports like `from deepagents.graph import create_deep_agent`
use the local source tree.

Usage examples
--------------
1) Use a local Ollama model (no cloud keys):
   - uv add langchain-ollama
   - export DEEPAGENTS_MODEL=ollama:llama3.1:8b
   - python examples/research/run_local.py "Write a short overview of LangGraph"

2) Use default Anthropic model (requires key):
   - export ANTHROPIC_API_KEY=...
   - python examples/research/run_local.py "what is langgraph?"

Optional: Tavily search
   - uv add tavily-python
   - export TAVILY_API_KEY=...
    If not configured, the `internet_search` tool returns a disabled message instead
    of failing, so the agent can still run fully locally.

Environment loading
-------------------
This script automatically loads environment variables from `.env` files without
overriding already-set variables:
 - examples/research/.env (preferred)
 - repo-root/.env (fallback)

Model selection
---------------
The script automatically detects your .env configuration and uses the appropriate provider:
- If DEEPAGENTS_MODEL_PROVIDER is set in .env, uses that provider configuration
- If DEEPAGENTS_MODEL is set, uses explicit model specification
- Otherwise falls back to a local default (Ollama)
Set FORCE_REPO_DEFAULT=1 to always use the repo default model.
"""

from __future__ import annotations

import os
import sys
from typing import Literal

# Ensure local repo sources are imported (not an installed wheel)
CURRENT_DIR = os.path.dirname(__file__)
REPO_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Load .env files (do not override pre-set env vars)
def _load_env_files():
    # Prefer a real dotenv if available
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(os.path.join(REPO_ROOT, ".env"), override=False)
        load_dotenv(os.path.join(CURRENT_DIR, ".env"), override=False)
        return
    except Exception:
        pass

    # Minimal fallback parser
    def _load_one(path: str):
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                for raw in f:
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = val
        except Exception:
            # Silently ignore malformed env files
            return

    # Load root first, then example-specific (example takes precedence for new keys)
    _load_one(os.path.join(REPO_ROOT, ".env"))
    _load_one(os.path.join(CURRENT_DIR, ".env"))


_load_env_files()

# Now we can import from the local source tree
from deepagents.graph import create_deep_agent
from deepagents.sub_agent import SubAgent

# Model selection: prefer env-specified model (e.g., Ollama), else default
try:
    from langchain.chat_models import init_chat_model  # available with langchain
except Exception:  # pragma: no cover - optional dep path
    init_chat_model = None  # type: ignore


KNOWN_PROVIDERS = {
    "ollama",
    "openai",
    "anthropic",
    "google",
    "vertexai",
    "cohere",
    "mistralai",
    "groq",
    "fireworks",
    "perplexity",
    "together",
    "azure",
    "openrouter",
    "deepseek",
    "bedrock",
}


def _init_model_from_string(model_str: str):
    if init_chat_model is None:
        raise RuntimeError(
            "`init_chat_model` is unavailable. Install the appropriate integration (e.g., `uv add langchain-ollama`)."
        )

    # If the string already has a known provider prefix, use as-is
    if ":" in model_str:
        prefix = model_str.split(":", 1)[0].lower()
        if prefix in KNOWN_PROVIDERS:
            return init_chat_model(model=model_str)

    # Otherwise, infer or require a provider
    provider = os.getenv("DEEPAGENTS_MODEL_PROVIDER")
    if not provider:
        # Heuristics: if Ollama integration/env looks present, default to ollama
        try:
            import langchain_ollama  # noqa: F401

            provider = "ollama"
        except Exception:
            pass
        if not provider and any(os.getenv(k) for k in ("OLLAMA_HOST", "OLLAMA_BASE_URL")):
            provider = "ollama"

    if not provider:
        raise RuntimeError(
            "Unable to infer model provider for model='{}'. Either prefix it (e.g., 'ollama:<tag>') "
            "or set DEEPAGENTS_MODEL_PROVIDER=ollama.".format(model_str)
        )

    return init_chat_model(model=model_str, model_provider=provider)


def get_model():
    """Resolve the chat model with safe defaults.

    Priority:
    1) Use explicit `DEEPAGENTS_MODEL` (provider inferred or specified).
    2) Check if .env has provider configuration and use repo's get_default_model().
    3) Otherwise, use local fallback (provider inferred or DEEPAGENTS_MODEL_PROVIDER).
    4) If `FORCE_REPO_DEFAULT=1`, always use the repo's `get_default_model()`.
    """
    model_id = os.getenv("DEEPAGENTS_MODEL")
    force_repo_default = os.getenv("FORCE_REPO_DEFAULT") == "1"

    if model_id:
        return _init_model_from_string(model_id)

    # Check if we have .env configuration for a provider
    provider = os.getenv("DEEPAGENTS_MODEL_PROVIDER")
    if provider or force_repo_default:
        # Use the repo's default model which respects .env configuration
        from deepagents.model import get_default_model
        return get_default_model()

    # Fallback to local default to avoid accidental cloud usage
    default_local = os.getenv("DEFAULT_LOCAL_MODEL", "ollama:llama3.1:8b")
    return _init_model_from_string(default_local)


# ----- Optional Tavily search tool -----
try:
    from tavily import TavilyClient  # type: ignore
except Exception:  # pragma: no cover - optional dep may be missing
    TavilyClient = None  # type: ignore

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
_tavily_client = None
if TavilyClient and TAVILY_API_KEY:
    try:
        _tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
    except Exception:
        _tavily_client = None


def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search (optional). Returns a disabled note if not configured."""
    if _tavily_client is None:
        return {
            "error": "Tavily search disabled: set TAVILY_API_KEY and install tavily-python to enable.",
            "query": query,
        }
    return _tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )


# ----- Sub-agent prompts -----
sub_research_prompt = """You are a dedicated researcher. Your job is to conduct research based on the users questions.

Conduct thorough research and then reply to the user with a detailed answer to their question.
Only your FINAL answer will be passed on to the user. They will have NO knowledge of anything except your final message, so your final report should be your final message!"""

research_sub_agent: SubAgent = {
    "name": "research-agent",
    "description": (
        "Used to research more in depth questions. Only give this researcher one topic at a time. "
        "Do not pass multiple sub questions to this researcher. Instead, break down a large topic into the necessary "
        "components, and then call multiple research agents in parallel, one for each sub question."
    ),
    "prompt": sub_research_prompt,
    "tools": ["internet_search"],
}

sub_critique_prompt = """You are a dedicated editor tasked to critique a report.

You can find the report at `final_report.md`.
You can find the question/topic for this report at `question.txt`.

Respond with a detailed critique of the report, pointing out specific areas for improvement.
You may use the search tool to validate facts, but do not write to `final_report.md` yourself.

Things to check:
- Appropriate, clear section names
- Written in paragraph form by default (not only bullet points)
- Comprehensive coverage and depth; identify missing or shallow sections
- Balanced analysis that directly addresses the research topic
- Clear structure and easy to understand
"""

critique_sub_agent: SubAgent = {
    "name": "critique-agent",
    "description": "Used to critique the final report.",
    "prompt": sub_critique_prompt,
}


# ----- Main agent instructions -----
research_instructions = """You are an expert researcher. Your job is to conduct thorough research, and then write a polished report.

The first thing you should do is to write the original user question to `question.txt` so you have a record of it.

Use the research-agent to conduct deep research. It will respond to your questions/topics with a detailed answer.
When you think you have enough information to write a final report, write it to `final_report.md`.
You can call the critique-agent to get a critique of the final report, iterate, and improve.

Only edit a single file at a time to avoid conflicts. Use clear markdown with `#` for title, `##` for sections, and `###` for subsections.
Include a Sources section with links. Ensure the final answer is in the same language as the user's question.

You have access to a few tools.

## `internet_search`
Use this to run an internet search for a given query. You can specify the number of results, the topic, and whether raw content should be included.
"""


def build_agent():
    model = get_model()
    agent = create_deep_agent(
        tools=[internet_search],
        instructions=research_instructions,
        model=model,
        subagents=[critique_sub_agent, research_sub_agent],
    ).with_config({"recursion_limit": int(os.getenv("RECURSION_LIMIT", "1000"))})
    return agent


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run the local Deep Research agent.")
    parser.add_argument("prompt", nargs="*", help="User question or task for the agent")
    parser.add_argument("--print-files", action="store_true", help="Print any files written by the agent")
    args = parser.parse_args()

    user_input = " ".join(args.prompt).strip() or os.getenv(
        "PROMPT", "Write a short overview of LangGraph without web search."
    )

    agent = build_agent()
    result = agent.invoke({"messages": [{"role": "user", "content": user_input}]})

    # Print the final assistant message
    messages = result.get("messages", [])
    if messages:
        print(messages[-1].content)
    else:
        print("[No messages returned]")

    if args.print_files:
        files = result.get("files") or {}
        if files:
            print("\n--- Files ---")
            for name, content in files.items():
                print(f"\n# {name}\n{content}")


# Expose a global `agent` for LangGraph Studio integration
agent = build_agent()


if __name__ == "__main__":
    main()

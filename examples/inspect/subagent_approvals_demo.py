#!/usr/bin/env python3
"""
Sub-agent + Approvals Demo (Examples Parity — Example 2)

This example demonstrates:
- Sub-agent handoff via a tool named `transfer_to_<name>`.
- Approval policy chaining, including a custom handoff exclusivity policy that
  skips other tool calls when a handoff is present in the same assistant turn.

It runs offline using a tiny in-process “model” for both the supervisor and
the sub-agent, so no API keys or network calls are required.

Usage
  uv run python examples/inspect/subagent_approvals_demo.py --preset dev

Presets
- ci: approve all tools
- dev: escalate sensitive tools; combined here with handoff exclusivity
- prod: terminate sensitive tools

What to expect
- The supervisor model proposes two tool calls in one turn:
  1) `transfer_to_researcher` (handoff to sub-agent)
  2) `write_file` (a sensitive operation)

- The `handoff_exclusive_policy()` approves the first handoff and rejects
  other tool calls in that same turn. As a result, only the handoff runs.
  The sub-agent then immediately submits the final answer.

Output includes the final completion and a list of executed tool functions
(`ChatMessageTool`) to show that `write_file` was skipped.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any


# --- Minimal path setup so imports work when run from repo root --------------
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
EXT_INSPECT_SRC = REPO_ROOT / "external" / "inspect_ai" / "src"
for p in (SRC_DIR, EXT_INSPECT_SRC):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


def _install_apply_if_missing() -> None:
    """Best-effort shim: ensure approval apply module exists.

    In normal use, the Inspect submodule provides this. This shim is a
    lightweight fallback for environments where it's not importable.
    """
    try:
        from inspect_ai.approval import _apply as _  # type: ignore
        return
    except Exception:
        pass

    import types

    apply_mod = types.ModuleType("inspect_ai.approval._apply")
    _policies: list[Any] | None = None

    def init_tool_approval(policies):  # pragma: no cover - simple wiring
        nonlocal _policies
        _policies = policies or []

    async def apply_tool_approval(message, call, viewer, history):  # pragma: no cover - simple wiring
        # Approve by default in the shim; real approval logic lives in Inspect.
        class _Approval:
            decision = "approve"
            modified = None
            explanation = None

        return True, _Approval()

    apply_mod.init_tool_approval = init_tool_approval
    apply_mod.apply_tool_approval = apply_tool_approval

    sys.modules["inspect_ai.approval._apply"] = apply_mod


def _build_demo_agent(preset: str):
    from inspect_ai.agent._agent import agent as as_agent
    from inspect_ai.model._chat_message import ChatMessageAssistant
    from inspect_ai.tool._tool_call import ToolCall

    from inspect_agents.agents import build_subagents, build_supervisor
    from inspect_agents.approval import (
        activate_approval_policies,
        approval_preset,
        handoff_exclusive_policy,
    )

    # --- Sub-agent: returns a submit tool call with an answer ---------------
    @as_agent(name="researcher", description="Researches and summarizes findings")
    def researcher_agent():
        async def _run(state, tools):  # pragma: no cover - trivial agent
            state.messages.append(
                ChatMessageAssistant(
                    content="",
                    tool_calls=[ToolCall(id="s", function="submit", arguments={"answer": "OK from researcher"})],
                )
            )
            return state

        return _run

    # Build handoff tool for the researcher (name → transfer_to_researcher)
    handoff_tools = build_subagents(
        configs=[dict(name="researcher", description="Researcher", prompt="Be concise.", model=researcher_agent())],
        base_tools=[],
    )

    # --- Supervisor model: propose a handoff AND a sensitive write_file ------
    @as_agent(name="supervisor", description="Routes work via tools and sub-agents")
    def supervisor_model():
        async def _run(state, tools):  # pragma: no cover - deterministic
            state.messages.append(
                ChatMessageAssistant(
                    content="",
                    tool_calls=[
                        ToolCall(id="1", function="transfer_to_researcher", arguments={}),
                        ToolCall(
                            id="2",
                            function="write_file",
                            arguments={"file_path": "sensitive.txt", "content": "topsecret"},
                        ),
                    ],
                )
            )
            return state

        return _run

    # Compose supervisor with handoff tool and our deterministic model
    agent = build_supervisor(
        prompt="You are the orchestrator.", tools=handoff_tools, attempts=1, model=supervisor_model()
    )

    # Activate approval policies: preset + handoff exclusivity
    policies = approval_preset(preset) + handoff_exclusive_policy()
    activate_approval_policies(policies)

    return agent


def main() -> None:
    _install_apply_if_missing()

    parser = argparse.ArgumentParser(description="Sub-agent + approvals demo (offline)")
    parser.add_argument("--preset", default=os.getenv("DEMO_APPROVAL_PRESET", "dev"), choices=["ci", "dev", "prod"])
    args = parser.parse_args()

    agent = _build_demo_agent(args.preset)

    # Run with an arbitrary prompt (our model ignores content)
    from inspect_agents.run import run_agent
    from inspect_ai.model._chat_message import ChatMessageTool

    result = asyncio.run(run_agent(agent, "start"))

    # Print final completion and executed tools for quick validation
    completion = getattr(result.output, "completion", None)
    print(f"Final completion: {completion}")

    executed_tools = [m.function for m in result.messages if isinstance(m, ChatMessageTool)]
    print("Executed tools:", executed_tools)
    print("Note: write_file should be skipped due to handoff exclusivity policy.")


if __name__ == "__main__":
    main()

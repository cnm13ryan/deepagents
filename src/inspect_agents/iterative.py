"""Iterative agent (ReAct-style stepper) for deepagents.

This mirrors the "iterative" concept from PaperBench's basic_agent_iterative:

- Drives the model with an initial system prompt, then repeatedly "nudges" it
  with a short, ephemeral "continue" instruction that is NOT persisted to the
  conversation history. The assistant's reply (and any tool results) ARE
  persisted, so the agent incrementally builds state while avoiding prompt
  blow‑up.
- Executes one tool call per step if the model requests it; otherwise injects
  a small user reminder to continue.
- Terminates on a real‑time limit (seconds) or a max step count.

The implementation returns an Inspect‑AI Agent (callable protocol) so it works
with `inspect_agents.run.run_agent(...)` the same way as `build_supervisor()`.

Defaults are conservative: we expose only the Files tools by default. To enable
execution (bash / python) or web search/browser, set the existing env flags used
by `inspect_agents.tools.standard_tools()` (e.g., INSPECT_ENABLE_EXEC=1).
"""

from __future__ import annotations

import asyncio
import os
import copy
import time
import logging
from typing import Any, Sequence

from inspect_ai.agent._agent import AgentState

logger = logging.getLogger(__name__)


def _format_progress_time(seconds: float) -> str:
    """Lightweight duration formatter (hh:mm:ss) to avoid importing internals."""
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _base_tools() -> list[object]:
    """Return a minimal toolset: Files tools + optional exec if enabled.

    We reuse our project tools to remain sandbox‑safe by default. Execution
    tools can be enabled via INSPECT_ENABLE_EXEC=1, which is honored by
    `standard_tools()`.
    """
    from .tools import edit_file, ls, read_file, standard_tools, write_file

    # Core FS tools are always available; append any enabled standard tools
    # (think, web_search, bash/python when INSPECT_ENABLE_EXEC=1, etc.).
    return [write_file(), read_file(), ls(), edit_file()] + standard_tools()


def _default_system_message() -> str:
    return (
        "You are an iterative coding agent.\n"
        "- Work in small, verifiable steps (one tool call per message).\n"
        "- Read or edit files as needed; keep the repo tidy and reproducible.\n"
        "- Prefer updating existing files over creating many new ones.\n"
        "- If a step requires execution, use bash responsibly and capture outputs.\n"
        "- Continue improving until time is up or explicit stop.\n"
    )


def _default_continue_message() -> str:
    return (
        "Now, given prior progress, take the next small step toward the goal. "
        "Use a tool if needed."
    )


def build_iterative_agent(
    *,
    prompt: str | None = None,
    tools: Sequence[object] | None = None,
    model: Any | None = None,
    real_time_limit_sec: int | None = None,
    max_steps: int | None = None,
    max_messages: int | None = None,
    continue_message: str | None = None,
    max_turns: int = 50,
    progress_every: int = 5,
    stop_on_keywords: Sequence[str] | None = None,
    # Conversation pruning (length-based)
    prune_after_messages: int | None = 120,
    prune_keep_last: int = 40,
) -> Any:
    """Create an Inspect agent that runs an iterative tool loop.

    Args:
        prompt: System instructions. If None, a sensible default is used.
        tools: Tools to expose. Defaults to Files tools plus any enabled standard tools.
        model: Inspect model identifier or object. If None, current active model is used.
        real_time_limit_sec: Wall‑clock time budget for the agent (excludes provider retry backoff best‑effort). If None, falls back to the env var `INSPECT_ITERATIVE_TIME_LIMIT` (seconds) when set.
        max_steps: Hard cap on loop steps. If None, falls back to the env var `INSPECT_ITERATIVE_MAX_STEPS` when set.
        max_messages: Absolute cap on retained message tail during pruning. When set, this takes precedence over the heuristic `2*max_turns` tail size.
        continue_message: Ephemeral user message appended each step (not persisted).

    Returns:
        Inspect Agent compatible with `inspect_ai.agent._run.run`.
    """

    # Local imports to avoid heavy imports at module import time in tests
    from inspect_ai.agent._agent import agent
    from inspect_ai.model._call_tools import call_tools
    from inspect_ai.model._chat_message import (
        ChatMessageAssistant,
        ChatMessageSystem,
        ChatMessageTool,
        ChatMessageUser,
    )
    from inspect_ai.model._generate_config import GenerateConfig
    from inspect_ai.model._model import get_model
    # Lightweight, provider-agnostic pruning
    try:
        from ._conversation import prune_messages
    except Exception:  # pragma: no cover - fallback if module unavailable
        prune_messages = None  # type: ignore

    sys_message = prompt or _default_system_message()
    step_nudge = continue_message or _default_continue_message()
    active_tools = list(tools or _base_tools())

    @agent(name="iterative_supervisor")
    def _iterative() -> Any:
        async def execute(state: AgentState) -> AgentState:
            # Resolve env fallbacks for limits when args are None
            _time_limit: int | None = real_time_limit_sec
            if _time_limit is None:
                try:
                    env_v = os.getenv("INSPECT_ITERATIVE_TIME_LIMIT")
                    if env_v is not None and str(env_v).strip() != "":
                        v = int(env_v)
                        _time_limit = v if v > 0 else None
                except Exception:
                    _time_limit = None

            _max_steps: int | None = max_steps
            if _max_steps is None:
                try:
                    env_v = os.getenv("INSPECT_ITERATIVE_MAX_STEPS")
                    if env_v is not None and str(env_v).strip() != "":
                        v = int(env_v)
                        _max_steps = v if v > 0 else None
                except Exception:
                    _max_steps = None

            # --- Pruning configuration -------------------------------------------------
            # Effective values for threshold-based prune and keep window.
            # Env overrides apply only when args are None/defaults to avoid
            # surprising callers who pass explicit values.
            _eff_prune_after: int | None = prune_after_messages
            _eff_prune_keep: int = prune_keep_last

            # Allow env to override threshold when arg is None or default (120)
            try:
                if prune_after_messages is None or prune_after_messages == 120:
                    env_after = os.getenv("INSPECT_PRUNE_AFTER_MESSAGES")
                    if env_after is not None and str(env_after).strip() != "":
                        v = int(env_after)
                        _eff_prune_after = v if v > 0 else None  # non-positive disables
            except Exception:
                # Keep existing value on parse errors
                pass

            # Allow env to override keep window when arg is default (40)
            try:
                if prune_keep_last == 40:
                    env_keep = os.getenv("INSPECT_PRUNE_KEEP_LAST")
                    if env_keep is not None and str(env_keep).strip() != "":
                        v = int(env_keep)
                        _eff_prune_keep = max(0, v)
            except Exception:
                pass

            # Enable prune debug logs if either INSPECT_PRUNE_DEBUG or
            # INSPECT_MODEL_DEBUG is set (reuse existing model debug toggle).
            _prune_debug: bool = bool(
                os.getenv("INSPECT_PRUNE_DEBUG") or os.getenv("INSPECT_MODEL_DEBUG")
            )

            # Advisory warning for very small max_messages caps
            if isinstance(max_messages, int) and 0 < max_messages < 6:
                try:
                    logger.warning(
                        "iterative: max_messages=%d is very small; recent context may be unstable.",
                        max_messages,
                    )
                except Exception:
                    pass

            # Ensure system prompt is present once at the head
            has_system = any(isinstance(m, ChatMessageSystem) for m in state.messages)
            if not has_system:
                state.messages = [ChatMessageSystem(content=sys_message)] + state.messages

            # Helper: prune history to keep context bounded while retaining
            # the first system + first user and the last window of turns.
            def _prune_history(messages: list[Any]) -> list[Any]:
                try:
                    from inspect_ai.model._chat_message import (
                        ChatMessageAssistant as _A,
                        ChatMessageSystem as _S,
                        ChatMessageTool as _T,
                        ChatMessageUser as _U,
                    )
                except Exception:
                    return messages

                # Determine pruning window size with precedence for max_messages
                if isinstance(max_messages, int) and max_messages > 0:
                    tail_window = max_messages
                elif max_turns is None or max_turns <= 0:
                    return messages
                else:
                    # Approximate: keep the last 2*max_turns messages from remaining
                    tail_window = max(0, 2 * int(max_turns))

                # Keep first system and first user messages (if present)
                first_sys_idx = next((i for i, m in enumerate(messages) if isinstance(m, _S)), None)
                first_user_idx = next((i for i, m in enumerate(messages) if isinstance(m, _U)), None)

                prefix_idxs: list[int] = []
                if isinstance(first_sys_idx, int):
                    prefix_idxs.append(first_sys_idx)
                if isinstance(first_user_idx, int) and first_user_idx not in prefix_idxs:
                    prefix_idxs.append(first_user_idx)
                prefix_idxs.sort()

                prefix = [messages[i] for i in prefix_idxs]
                # Remaining messages (preserve order) excluding chosen prefix
                remaining = [m for i, m in enumerate(messages) if i not in prefix_idxs]

                tail = remaining[-tail_window:] if tail_window else remaining

                # Drop orphan tool messages that are not immediately following an assistant
                filtered_tail: list[Any] = []
                last_was_assistant = False
                for m in tail:
                    if isinstance(m, _A):
                        filtered_tail.append(m)
                        last_was_assistant = True
                    elif isinstance(m, _T):
                        if last_was_assistant:
                            filtered_tail.append(m)
                        # tools do not change assistant/user state
                    else:
                        # user/system or other -> reset assistant streak
                        filtered_tail.append(m)
                        last_was_assistant = False

                return prefix + filtered_tail

            start = time.time()
            step = 0
            # Accept either an Inspect Model spec or a model-like object with `generate()`
            if model is not None and hasattr(model, "generate"):
                model_obj = model  # custom test/dummy model passed directly
            else:
                model_obj = get_model(model) if model is not None else get_model()

            # Main loop
            while True:
                step += 1

                # Time budget
                if _time_limit is not None:
                    elapsed = time.time() - start
                    if elapsed >= _time_limit:
                        break

                # Step budget
                if _max_steps is not None and step > _max_steps:
                    break

                # Progress ping every N steps (persisted)
                if progress_every and step % int(progress_every) == 0:
                    elapsed = time.time() - start
                    state.messages.append(
                        ChatMessageUser(
                            content=(
                                f"Info: {_format_progress_time(int(elapsed))} elapsed"
                            )
                        )
                    )

                # Prune history to bound growth
                try:
                    state.messages = _prune_history(state.messages)
                except Exception:
                    # Best-effort only; continue if pruning fails
                    pass

                # Opportunistic global prune when message list exceeds threshold
                try:
                    if (
                        prune_messages
                        and _eff_prune_after is not None
                        and len(state.messages) > _eff_prune_after
                    ):
                        _pre = len(state.messages)
                        state.messages = prune_messages(
                            state.messages, keep_last=_eff_prune_keep
                        )
                        if _prune_debug:
                            logger.info(
                                "Prune: reason=threshold pre=%d post=%d keep_last=%d threshold=%s",
                                _pre,
                                len(state.messages),
                                int(_eff_prune_keep),
                                "None" if _eff_prune_after is None else int(_eff_prune_after),
                            )
                except Exception:
                    pass

                # Build ephemeral conversation with a nudge but don't persist the nudge
                conversation = copy.deepcopy(state.messages) + [
                    ChatMessageUser(content=step_nudge)
                ]

                # Compute per-call timeout so we do not run past the budget
                gen_timeout: int | None = None
                if _time_limit is not None:
                    remaining = int(_time_limit - (time.time() - start))
                    gen_timeout = max(1, remaining) if remaining > 0 else 1

                length_overflow = False
                try:
                    output = await model_obj.generate(
                        input=conversation,
                        tools=active_tools,
                        cache=False,
                        config=GenerateConfig(timeout=gen_timeout),
                    )
                    state.output = output
                    state.messages.append(output.message)
                except IndexError:
                    length_overflow = True

                # If model hit length limits, append a small hint and continue
                if length_overflow or (getattr(state.output, "stop_reason", None) == "model_length"):
                    state.messages.append(
                        ChatMessageUser(
                            content=(
                                "Context too long; please summarize recent steps and continue."
                            )
                        )
                    )
                    # Apply pruning immediately after overflow to reduce context
                    try:
                        if prune_messages:
                            _pre = len(state.messages)
                            state.messages = prune_messages(
                                state.messages, keep_last=_eff_prune_keep
                            )
                            if _prune_debug:
                                logger.info(
                                    "Prune: reason=overflow pre=%d post=%d keep_last=%d",
                                    _pre,
                                    len(state.messages),
                                    int(_eff_prune_keep),
                                )
                    except Exception:
                        pass
                    continue

                # Resolve tool calls (if any)
                msg = state.output.message if hasattr(state, "output") else None
                tool_calls = getattr(msg, "tool_calls", None) if msg else None
                if tool_calls:
                    # Per‑call timeout equals remaining budget
                    timeout_ctx = None
                    if _time_limit is not None:
                        remaining = _time_limit - (time.time() - start)
                        timeout_ctx = max(1, int(remaining)) if remaining > 0 else 1

                    try:
                        if timeout_ctx is not None:
                            async with asyncio.timeout(timeout_ctx):
                                results = await call_tools(msg, active_tools)
                        else:
                            results = await call_tools(msg, active_tools)
                    except asyncio.TimeoutError:
                        state.messages.append(
                            ChatMessageUser(content="Timeout: The tool call timed out.")
                        )
                        break

                    # Persist tool results
                    if isinstance(results, list):
                        for r in results:
                            if isinstance(r, ChatMessageTool):
                                state.messages.append(r)
                    # Continue to the next step
                else:
                    # No tool used; encourage the model to take an action
                    state.messages.append(ChatMessageUser(content="Please continue."))

                # Guard: if the assistant just said it is done, exit early
                last = state.messages[-1] if state.messages else None
                if isinstance(last, ChatMessageAssistant):
                    if stop_on_keywords:
                        txt = (last.text or "").strip().lower()
                        if any(k.lower() in txt for k in stop_on_keywords):
                            break

            return state

        return execute

    return _iterative()


__all__ = ["build_iterative_agent"]

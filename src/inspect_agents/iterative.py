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
import copy
import logging
import os
import time
from collections.abc import Callable, Sequence
from typing import Any

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
    # Soft in-loop sample limits (agent-level; default None to preserve behavior)
    message_limit: int | None = None,
    token_limit: int | None = None,
    continue_message: str | None = None,
    max_turns: int = 50,
    progress_every: int = 5,
    stop_on_keywords: Sequence[str] | None = None,
    # Unified global tool-output cap (bytes). Explicit param > env > default.
    max_tool_output_bytes: int | None = None,
    # Conversation pruning (length-based)
    prune_after_messages: int | None = 120,
    prune_keep_last: int = 40,
    # Token-aware overflow control (per-message cap; default off)
    per_msg_token_cap: int | None = None,
    truncate_last_k: int = 200,
    # Optional injections for deterministic testing (kw-only, default real time)
    clock: Callable[[], float] = time.time,
    timeout_factory: Callable[[int], Any] = asyncio.timeout,
) -> Any:
    """Create an Inspect agent that runs an iterative tool loop.

    Args:
        prompt: System instructions. If None, a sensible default is used.
        tools: Tools to expose. Defaults to Files tools plus any enabled standard tools.
        model: Inspect model identifier or object. If None, current active model is used.
        real_time_limit_sec: Wall‑clock time budget for the agent (excludes provider retry backoff best‑effort). If None, falls back to the env var `INSPECT_ITERATIVE_TIME_LIMIT` (seconds) when set.
        max_steps: Hard cap on loop steps. If None, falls back to the env var `INSPECT_ITERATIVE_MAX_STEPS` when set.
        max_messages: Absolute cap on retained message tail during pruning. When set, this takes precedence over the heuristic `2*max_turns` tail size.
        message_limit: Optional hard cap on total messages in the conversation. When the limit is met at the start of a loop iteration, the agent appends a final user message explaining the limit and stops. This is an agent-level soft stop and is independent of runner limits.
        token_limit: Optional approximate cap on total tokens across the conversation. Evaluated at the start of each loop iteration using a lightweight estimator (tiktoken when available; otherwise a char/4 heuristic). On overflow, append a final explanatory user message and stop. This is agent-level and independent of runner limits.
        continue_message: Ephemeral user message appended each step (not persisted).

    Returns:
        Inspect Agent compatible with `inspect_ai.agent._run.run`.
    """

    # Local imports to avoid heavy imports at module import time in tests
    from inspect_ai.agent._agent import agent
    from inspect_ai.model._call_tools import execute_tools
    from inspect_ai.model._chat_message import (
        ChatMessageAssistant,
        ChatMessageSystem,
        ChatMessageUser,
    )
    from inspect_ai.model._generate_config import GenerateConfig
    # Early config APIs for global tool-output cap
    try:
        from inspect_ai.model._generate_config import (
            active_generate_config,
            set_active_generate_config,
        )
    except Exception:  # pragma: no cover - defensive: allow older upstream
        active_generate_config = None  # type: ignore
        set_active_generate_config = None  # type: ignore
    from inspect_ai.model._model import get_model
    # Lightweight, provider-agnostic pruning
    try:
        from ._conversation import (
            prune_messages,
            truncate_conversation_tokens,
        )
    except Exception:  # pragma: no cover - fallback if module unavailable
        prune_messages = None  # type: ignore
        truncate_conversation_tokens = None  # type: ignore

    sys_message = prompt or _default_system_message()
    step_nudge = continue_message or _default_continue_message()
    active_tools = list(tools or _base_tools())

    @agent(name="iterative_supervisor")
    def _iterative() -> Any:
        async def execute(state: AgentState) -> AgentState:
            # ------------------------------------------------------------------
            # Early, unified tool-output cap (before any generate/tool execution)
            # Precedence: explicit param > active GenerateConfig > env > default
            try:
                # Parse env override only if explicit param not provided
                def _parse_int(v: str | None) -> int | None:
                    try:
                        if v is None:
                            return None
                        iv = int(str(v).strip())
                        return iv if iv >= 0 else None
                    except Exception:
                        return None

                _env_limit = _parse_int(os.getenv("INSPECT_MAX_TOOL_OUTPUT"))
                if active_generate_config and set_active_generate_config:
                    cfg = active_generate_config()
                    if max_tool_output_bytes is not None:
                        try:
                            new_cfg = cfg.merge({"max_tool_output": int(max_tool_output_bytes)})  # type: ignore[arg-type]
                            set_active_generate_config(new_cfg)
                        except Exception:
                            try:
                                cfg.max_tool_output = int(max_tool_output_bytes)  # type: ignore[attr-defined]
                            except Exception:
                                pass
                    elif _env_limit is not None and getattr(cfg, "max_tool_output", None) is None:
                        try:
                            new_cfg = cfg.merge({"max_tool_output": int(_env_limit)})  # type: ignore[arg-type]
                            set_active_generate_config(new_cfg)
                        except Exception:
                            try:
                                cfg.max_tool_output = int(_env_limit)  # type: ignore[attr-defined]
                            except Exception:
                                pass
            except Exception:
                # Best-effort only; do not block agent startup on config issues
                pass

            # Resolve limits/pruning/truncation using pure helpers
            from .iterative_config import (
                resolve_pruning,
                resolve_time_and_step_limits,
                resolve_truncation,
            )

            _time_limit, _max_steps = resolve_time_and_step_limits(
                real_time_limit_sec=real_time_limit_sec,
                max_steps=max_steps,
            )

            _eff_prune_after, _eff_prune_keep = resolve_pruning(
                prune_after_messages=prune_after_messages,
                prune_keep_last=prune_keep_last,
            )

            _eff_token_cap, _eff_truncate_last_k = resolve_truncation(
                per_msg_token_cap=per_msg_token_cap,
                truncate_last_k=truncate_last_k,
            )

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
                        ChatMessageAssistant,
                        ChatMessageSystem,
                        ChatMessageTool,
                        ChatMessageUser,
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
                first_sys_idx = next((i for i, m in enumerate(messages) if isinstance(m, ChatMessageSystem)), None)
                first_user_idx = next((i for i, m in enumerate(messages) if isinstance(m, ChatMessageUser)), None)

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
                    if isinstance(m, ChatMessageAssistant):
                        filtered_tail.append(m)
                        last_was_assistant = True
                    elif isinstance(m, ChatMessageTool):
                        if last_was_assistant:
                            filtered_tail.append(m)
                        # tools do not change assistant/user state
                    else:
                        # user/system or other -> reset assistant streak
                        filtered_tail.append(m)
                        last_was_assistant = False

                return prefix + filtered_tail

            start = clock()
            # Track total backoff/wait introduced by provider retries handled by
            # our local generate() wrapper. When INSPECT_PRODUCTIVE_TIME=1 is
            # enabled, we subtract this from elapsed time for budget/timeout.
            total_retry_time: float = 0.0
            productive_time_enabled: bool = bool(
                os.getenv("INSPECT_PRODUCTIVE_TIME")
            )
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
                    _wall = clock() - start
                    _elapsed = (
                        _wall - total_retry_time if productive_time_enabled else _wall
                    )
                    if _elapsed >= _time_limit:
                        break

                # Step budget
                if _max_steps is not None and step > _max_steps:
                    break

                # --------------------------------------------------------------
                # Agent-level soft limits (message/token) — early, before I/O
                # These are evaluated at the start of each loop iteration to
                # provide a clear, user-visible stop without raising errors.
                try:
                    # Message count limit
                    if isinstance(message_limit, int) and message_limit > 0:
                        if len(state.messages) >= int(message_limit):
                            state.messages.append(
                                ChatMessageUser(
                                    content=f"[limit] Message limit reached ({len(state.messages)}). Stopping."
                                )
                            )
                            break
                except Exception:
                    # Non-fatal: ignore counting failure
                    pass

                # Token budget limit (approximate)
                try:
                    if isinstance(token_limit, int) and token_limit > 0:
                        def _extract_text(m: Any) -> str:
                            # Prefer .text when present; else flatten string content; else best-effort
                            try:
                                txt = getattr(m, "text", None)
                                if isinstance(txt, str) and txt:
                                    return txt
                            except Exception:
                                pass
                            c = getattr(m, "content", None)
                            if isinstance(c, str):
                                return c
                            if isinstance(c, list):
                                parts: list[str] = []
                                for item in c:
                                    try:
                                        if isinstance(item, dict):
                                            t = item.get("type")
                                            if t == "text" and isinstance(item.get("text"), str):
                                                parts.append(item.get("text", ""))
                                            elif t == "reasoning" and isinstance(item.get("reasoning"), str):
                                                parts.append(item.get("reasoning", ""))
                                        else:
                                            t = getattr(item, "type", None)
                                            if t == "text":
                                                parts.append(str(getattr(item, "text", "")))
                                            elif t == "reasoning":
                                                parts.append(str(getattr(item, "reasoning", "")))
                                    except Exception:
                                        continue
                                return "\n".join(parts)
                            return ""

                        all_text = []
                        for msg in state.messages:
                            try:
                                all_text.append(_extract_text(msg))
                            except Exception:
                                all_text.append("")
                        corpus = "\n".join([t for t in all_text if isinstance(t, str)])

                        approx_tokens: int = 0
                        try:
                            # Best effort: use tiktoken o200k_base if available
                            import tiktoken  # type: ignore

                            try:
                                enc = tiktoken.get_encoding("o200k_base")
                            except Exception:
                                enc = None
                            if enc is not None:
                                approx_tokens = int(len(enc.encode(corpus, disallowed_special=())))
                            else:
                                raise RuntimeError("no-encoder")
                        except Exception:
                            # Fallback heuristic: ~4 chars per token
                            try:
                                approx_tokens = int((len(corpus) + 3) // 4)
                            except Exception:
                                approx_tokens = 0

                        if approx_tokens >= int(token_limit):
                            state.messages.append(
                                ChatMessageUser(
                                    content=f"[limit] Token limit reached (~{approx_tokens}). Stopping."
                                )
                            )
                            break
                except Exception:
                    # Non-fatal: ignore token estimation errors
                    pass

                # Progress ping every N steps (persisted)
                if progress_every and step % int(progress_every) == 0:
                    _wall = clock() - start
                    _elapsed = (
                        _wall - total_retry_time if productive_time_enabled else _wall
                    )
                    # Emit an info log with wall, retry accrual, and productive elapsed
                    try:
                        logger.info(
                            "iterative progress: elapsed=%.2fs retry=%.2fs productive=%.2fs step=%d",
                            float(_wall),
                            float(total_retry_time),
                            float(max(0.0, _elapsed)),
                            int(step),
                        )
                    except Exception:
                        pass
                    state.messages.append(
                        ChatMessageUser(
                            content=(f"Info: {_format_progress_time(int(_wall))} elapsed")
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
                        # First, token-aware truncation over the last K messages (if enabled)
                        try:
                            if truncate_conversation_tokens and _eff_token_cap is not None:
                                _pre_tokens = len(state.messages)
                                state.messages = truncate_conversation_tokens(
                                    state.messages,
                                    max_tokens_per_msg=int(_eff_token_cap),
                                    last_k=int(_eff_truncate_last_k),
                                )
                                if _prune_debug:
                                    logger.info(
                                        "Truncate: reason=threshold size_pre=%d last_k=%d cap=%d",
                                        _pre_tokens,
                                        int(_eff_truncate_last_k),
                                        int(_eff_token_cap),
                                    )
                        except Exception:
                            pass
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
                    _wall = clock() - start
                    _rem = _time_limit - (
                        (_wall - total_retry_time) if productive_time_enabled else _wall
                    )
                    remaining = int(_rem)
                    gen_timeout = max(1, remaining) if remaining > 0 else 1

                length_overflow = False
                try:
                    # Always route through our retry wrapper so we can account for
                    # provider backoff time (subtract when feature enabled).
                    from ._model_retry import generate_with_retry_time

                    output, retry_wait = await generate_with_retry_time(
                        model_obj,
                        input=conversation,
                        tools=active_tools,
                        cache=False,
                        config=GenerateConfig(timeout=gen_timeout),
                    )
                    # Accrue retry wait and persist model output
                    try:
                        total_retry_time += float(retry_wait or 0.0)
                    except Exception:
                        pass
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
                            # Token-aware truncation first (if enabled)
                            try:
                                if truncate_conversation_tokens and _eff_token_cap is not None:
                                    _pre_tokens = len(state.messages)
                                    state.messages = truncate_conversation_tokens(
                                        state.messages,
                                        max_tokens_per_msg=int(_eff_token_cap),
                                        last_k=int(_eff_truncate_last_k),
                                    )
                                    if _prune_debug:
                                        logger.info(
                                            "Truncate: reason=overflow size_pre=%d last_k=%d cap=%d",
                                            _pre_tokens,
                                            int(_eff_truncate_last_k),
                                            int(_eff_token_cap),
                                        )
                            except Exception:
                                pass
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
                        _wall = clock() - start
                        _rem = _time_limit - (
                            (_wall - total_retry_time)
                            if productive_time_enabled
                            else _wall
                        )
                        timeout_ctx = max(1, int(_rem)) if _rem > 0 else 1

                    try:
                        # Helper to feature-detect max_output support at runtime.
                        async def _exec_tools(messages: list[Any], tools: Sequence[object], max_output: int | None):
                            try:
                                return await execute_tools(messages, tools, max_output=max_output)  # type: ignore[call-arg]
                            except TypeError:
                                # Older API without max_output kwarg
                                return await execute_tools(messages, tools)  # type: ignore[misc]

                        _max_out = int(max_tool_output_bytes) if max_tool_output_bytes is not None else None
                        if timeout_ctx is not None:
                            async with timeout_factory(timeout_ctx):
                                exec_res = await _exec_tools(state.messages, active_tools, _max_out)
                        else:
                            exec_res = await _exec_tools(state.messages, active_tools, _max_out)
                    except TimeoutError:
                        state.messages.append(
                            ChatMessageUser(content="Timeout: The tool call timed out.")
                        )
                        break

                    # Persist tool execution results (messages + possible output)
                    for m in getattr(exec_res, "messages", []) or []:
                        state.messages.append(m)
                    if getattr(exec_res, "output", None) is not None:
                        state.output = exec_res.output
                    # Continue to the next step
                else:
                    # No tool used; encourage the model to take an action.
                    # Avoid appending a nudge if we have reached the final step
                    will_exceed_steps = _max_steps is not None and step >= _max_steps
                    # Append the nudge if we are not at the last step, or if
                    # per-message truncation is disabled (tests expect the nudge
                    # to be present in that case even on the final step).
                    if (not will_exceed_steps) or (_eff_token_cap is None):
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

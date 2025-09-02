from __future__ import annotations

# ruff: noqa: E402
"""Quarantine filters and defaults for Inspect handoffs.

Provides strict/scoped input filters and repo-wide env-driven defaults.
"""

from typing import Any
from collections.abc import Awaitable, Callable
import json
import os
import logging


Message = Any  # defer to inspect_ai.model._chat_message.ChatMessage at runtime
MessageFilter = Callable[[list[Message]], Awaitable[list[Message]]]

# Key used in Inspect Store to record the currently active input filter.
# This lives in the per-(sub)task store so nested handoffs inherit it without
# leaking to siblings when control returns to the parent task.
ACTIVE_INPUT_FILTER_KEY = "inspect_agents:active_input_filter_mode"


def _truthy(val: str | None) -> bool:
    if val is None:
        return False
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _compose_filters(*filters: MessageFilter) -> MessageFilter:
    async def run(messages: list[Message]) -> list[Message]:
        out = messages
        for f in filters:
            out = await f(out)
        return out

    return run


def _identity_filter() -> MessageFilter:
    async def run(messages: list[Message]) -> list[Message]:
        return messages

    return run


def strict_quarantine_filter() -> MessageFilter:
    """Strict quarantine: remove tools/system, keep only boundary message.

    Composes Inspect's remove_tools -> content_only -> last_message.
    Returns an identity filter if Inspect is unavailable.
    """
    try:
        from inspect_ai.agent._filter import remove_tools, content_only, last_message

        return _compose_filters(remove_tools, content_only, last_message)
    except Exception:
        # In stubbed environments fall back to a no-op
        return _identity_filter()


def _append_scoped_summary_factory(max_todos: int = 10, max_files: int = 20, max_bytes: int = 2048) -> MessageFilter:
    async def run(messages: list[Message]) -> list[Message]:
        # Late imports to avoid heavy deps at module import time
        try:
            from inspect_ai.util._store_model import store
            from inspect_ai.util._store_model import store_as
            from inspect_ai.model._chat_message import ChatMessageUser
            from .state import Todos, Files
        except Exception:
            return messages

        try:
            _ = store()  # ensure a store is active
            todos_model = store_as(Todos)
            files_model = store_as(Files)
            todos = [
                {"content": (t.content if len(t.content) <= 200 else t.content[:200]), "status": t.status}
                for t in (todos_model.get_todos() or [])
            ][: max(0, max_todos)]
            file_names = files_model.list_files() if hasattr(files_model, "list_files") else []
            files_list = list(file_names)[: max(0, max_files)]
            remaining = max(0, len(file_names) - len(files_list))
            payload = {
                "version": "v1",
                "scope": "scoped",
                "todos": todos,
                "files": {"list": files_list, "remaining_count": remaining},
            }
            data = json.dumps(payload, ensure_ascii=False)
            # size guard: if oversized, trim files first then todos
            logger = logging.getLogger(__name__)
            original_bytes = len(data.encode("utf-8"))
            trimmed = False
            if len(data.encode("utf-8")) > max_bytes:
                # progressively trim
                while files_list and len(data.encode("utf-8")) > max_bytes:
                    files_list.pop()
                    payload["files"]["list"] = files_list  # type: ignore[index]
                    data = json.dumps(payload, ensure_ascii=False)
                    trimmed = True
                while todos and len(data.encode("utf-8")) > max_bytes:
                    todos.pop()
                    payload["todos"] = todos
                    data = json.dumps(payload, ensure_ascii=False)
                    trimmed = True

            final_bytes = len(data.encode("utf-8"))
            try:
                logger.info(
                    "scoped_summary size_bytes=%d->%d todos=%d files_listed=%d files_remaining=%d trimmed=%s",
                    original_bytes,
                    final_bytes,
                    len(payload.get("todos", [])),
                    len(payload.get("files", {}).get("list", [])),  # type: ignore[attr-defined]
                    payload.get("files", {}).get("remaining_count", 0),  # type: ignore[attr-defined]
                    trimmed,
                )
            except Exception:
                pass

            return messages + [ChatMessageUser(content=data)]
        except Exception:
            return messages

    return run


def _int_env(name: str, default: int, minimum: int = 0) -> int:
    try:
        val = int(os.getenv(name, str(default)))
        return max(minimum, val)
    except Exception:
        return default


def scoped_quarantine_filter(include_state_summary: bool = True) -> MessageFilter:
    """Scoped quarantine: strict filter with optional JSON state summary.

    Returns an identity filter if Inspect is unavailable.
    """
    strict = strict_quarantine_filter()
    if include_state_summary:
        max_bytes = _int_env("INSPECT_SCOPED_MAX_BYTES", 2048, 512)
        max_todos = _int_env("INSPECT_SCOPED_MAX_TODOS", 10, 0)
        max_files = _int_env("INSPECT_SCOPED_MAX_FILES", 20, 0)
        summary = _append_scoped_summary_factory(max_todos=max_todos, max_files=max_files, max_bytes=max_bytes)
    else:
        summary = _identity_filter()
    return _compose_filters(strict, summary)

def _filter_for_mode(mode: str) -> MessageFilter:
    mode = (mode or "strict").strip().lower()
    if mode == "off":
        return _identity_filter()
    if mode == "scoped":
        return scoped_quarantine_filter(include_state_summary=True)
    # default strict
    return strict_quarantine_filter()


def _normalize_agent_env_suffix(name: str) -> str:
    """Normalise agent suffix for per-agent env overrides.

    - lower-case letters
    - replace any non-alphanumeric char with underscore
    - collapse multiple underscores and strip leading/trailing underscores
    Example: "Research Assistant v2" -> "research_assistant_v2"
    """
    import re
    lower = (name or "").lower()
    replaced = re.sub(r"[^a-z0-9]+", "_", lower)
    collapsed = re.sub(r"_+", "_", replaced).strip("_")
    return collapsed


def _per_agent_env_mode(agent_name: str | None) -> str | None:
    if not agent_name:
        return None
    suffix = _normalize_agent_env_suffix(agent_name)
    key = f"INSPECT_QUARANTINE_MODE__{suffix}"
    val = os.getenv(key)
    return val


def default_input_filter(agent_name: str | None = None) -> MessageFilter:
    """Return a context-aware input filter that supports cascading.

    Precedence when no explicit filter is set on the sub-agent:
    1) Per-agent env override: INSPECT_QUARANTINE_MODE__<AGENT_NAME>
    2) If should_inherit_filters() and a parent active filter is present in the
       Store (ACTIVE_INPUT_FILTER_KEY), cascade that filter
    3) Fallback to global env INSPECT_QUARANTINE_MODE (default: strict)

    The chosen filter is recorded into the Store before being applied so that
    nested handoffs inherit it within the subtask context.
    """

    async def run(messages: list[Message]) -> list[Message]:
        # Late imports to avoid hard dependency at module import
        try:
            from inspect_ai.util._store import store
        except Exception:
            # If Store is unavailable, just use env/global default
            per_agent = _per_agent_env_mode(agent_name)
            mode = per_agent if per_agent is not None else os.getenv("INSPECT_QUARANTINE_MODE", "strict")
            chosen = _filter_for_mode(mode)
            return await chosen(messages)

        # 1) Per-agent env override (treat as explicit)
        per_agent = _per_agent_env_mode(agent_name)
        if per_agent is not None:
            chosen = _filter_for_mode(per_agent)
            try:
                store().set(ACTIVE_INPUT_FILTER_KEY, per_agent)
            except Exception:
                pass
            return await chosen(messages)

        # 2) Cascade parent active filter if enabled and present
        chosen: MessageFilter
        if should_inherit_filters():
            try:
                active_mode = store().get(ACTIVE_INPUT_FILTER_KEY, None)
            except Exception:
                active_mode = None
            if isinstance(active_mode, str) and active_mode:
                chosen = _filter_for_mode(active_mode)
            else:
                chosen = _filter_for_mode(os.getenv("INSPECT_QUARANTINE_MODE", "strict"))
        else:
            # Inherit disabled: use global default only
            chosen = _filter_for_mode(os.getenv("INSPECT_QUARANTINE_MODE", "strict"))

        # Record chosen so nested sub-handoffs inherit within this subtask
        try:
            # Persist mode string if resolvable; otherwise assume strict
            mode_str = per_agent or (
                active_mode
                if isinstance(locals().get("active_mode"), str)
                else os.getenv("INSPECT_QUARANTINE_MODE", "strict")
            )
            store().set(ACTIVE_INPUT_FILTER_KEY, mode_str)
        except Exception:
            pass

        return await chosen(messages)

    return run


def default_output_filter() -> MessageFilter | None:
    """Return a safe default output filter (content_only) if available."""
    try:
        from inspect_ai.agent._filter import content_only

        return content_only
    except Exception:
        return None


def should_inherit_filters() -> bool:
    """Return whether to apply default input filters to sub-handoffs.

    Controlled by INSPECT_QUARANTINE_INHERIT (default: true).
    """
    env = os.getenv("INSPECT_QUARANTINE_INHERIT")
    return True if env is None else _truthy(env)


__all__ = [
    "MessageFilter",
    "strict_quarantine_filter",
    "scoped_quarantine_filter",
    "default_input_filter",
    "default_output_filter",
    "should_inherit_filters",
    "ACTIVE_INPUT_FILTER_KEY",
]

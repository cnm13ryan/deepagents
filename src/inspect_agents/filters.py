from __future__ import annotations

"""Quarantine filters and defaults for Inspect handoffs.

Provides strict/scoped input filters and repo-wide env-driven defaults.
"""

from typing import Any, Awaitable, Callable, List, Optional
import json
import os
import logging


Message = Any  # defer to inspect_ai.model._chat_message.ChatMessage at runtime
MessageFilter = Callable[[List[Message]], Awaitable[List[Message]]]


def _truthy(val: Optional[str]) -> bool:
    if val is None:
        return False
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _compose_filters(*filters: MessageFilter) -> MessageFilter:
    async def run(messages: List[Message]) -> List[Message]:
        out = messages
        for f in filters:
            out = await f(out)
        return out

    return run


def _identity_filter() -> MessageFilter:
    async def run(messages: List[Message]) -> List[Message]:
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
    async def run(messages: List[Message]) -> List[Message]:
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


def default_input_filter() -> MessageFilter:
    """Return the repo-wide default input filter based on env.

    INSPECT_QUARANTINE_MODE: strict (default) | scoped | off
    """
    mode = (os.getenv("INSPECT_QUARANTINE_MODE") or "strict").strip().lower()
    if mode == "off":
        return _identity_filter()
    if mode == "scoped":
        return scoped_quarantine_filter(include_state_summary=True)
    return strict_quarantine_filter()


def default_output_filter() -> Optional[MessageFilter]:
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
]

"""Conversation pruning utilities.

Lightweight, provider-agnostic helpers to bound conversation growth while
preserving coherence:
- keep all system messages;
- keep the first user message;
- keep the last N user/assistant/tool messages with correct tool pairing
  (a ChatMessageTool is preserved only if its parent assistant message with the
  matching tool call id is also kept).

No tokenizer is required; this is list-length based. Token-aware strategies can
be layered later without changing the public surface.

Doctest smoke (structure-only):
>>> from types import SimpleNamespace as NS
>>> sys = NS(role="system", content="S")
>>> u1 = NS(role="user", content="U1")
>>> a1 = NS(role="assistant", content="", tool_calls=[NS(id="1", function="ls", arguments={})])
>>> t1 = NS(role="tool", tool_call_id="1", content="ok")
>>> junk = NS(role="assistant", content="Context too long; please summarize recent steps and continue.")
>>> tail = [NS(role="user", content=f"U{i}") for i in range(2, 8)]
>>> msgs = [sys, u1, a1, t1, junk] + tail
>>> pruned = prune_messages(msgs, keep_last=4)
>>> pruned[0].role, pruned[1].role
('system', 'user')
>>> any(m is junk for m in pruned)
False
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def _is_system(msg: Any) -> bool:
    return getattr(msg, "role", None) == "system"


def _is_user(msg: Any) -> bool:
    return getattr(msg, "role", None) == "user"


def _is_assistant(msg: Any) -> bool:
    return getattr(msg, "role", None) == "assistant"


def _is_tool(msg: Any) -> bool:
    return getattr(msg, "role", None) == "tool"


def _assistant_tool_call_ids(msg: Any) -> set[str]:
    """Return set of tool_call ids from an assistant message, if any."""
    ids: set[str] = set()
    try:
        for tc in getattr(msg, "tool_calls", []) or []:
            _id = getattr(tc, "id", None)
            if isinstance(_id, str) and _id:
                ids.add(_id)
    except Exception:
        pass
    return ids


def _collect_parented_tool_ids(messages: Iterable[Any]) -> set[str]:
    ids: set[str] = set()
    for m in messages:
        if _is_assistant(m):
            ids.update(_assistant_tool_call_ids(m))
    return ids


_OVERFLOW_HINT = "Context too long; please summarize recent steps and continue."


def prune_messages(messages: list[Any], keep_last: int = 40) -> list[Any]:
    """Return a bounded conversation preserving system, first user, and last tail.

    Rules:
    - Preserve all system messages (in original order).
    - Preserve the first user message (if any).
    - From the remainder, keep the last `keep_last` messages where role is one of
      user/assistant/tool. Then drop any tool message whose `tool_call_id` is not
      present in a kept assistant message's tool_calls.
    - Drop overflow-hint placeholders injected by the iterative agent.
    """
    keep_last = max(0, int(keep_last))

    # Partition
    systems: list[Any] = [m for m in messages if _is_system(m)]
    first_user: list[Any] = []
    for m in messages:
        if _is_user(m):
            first_user = [m]
            break

    # Filter out overflow hint placeholders everywhere
    def _not_hint(m: Any) -> bool:
        try:
            txt = (getattr(m, "content", None) or "").strip()
            return txt != _OVERFLOW_HINT
        except Exception:
            return True

    core = [m for m in messages if m not in systems and (not first_user or m is not first_user[0])]
    core = [m for m in core if _not_hint(m)]

    # Take last N assistant/user/tool messages
    tail: list[Any] = []
    for m in reversed(core):
        if _is_assistant(m) or _is_user(m) or _is_tool(m):
            tail.append(m)
            if len(tail) >= keep_last:
                break
    tail.reverse()

    # Ensure tool pairing: only keep tool messages if their parent assistant call exists
    parent_ids = _collect_parented_tool_ids(tail)
    pruned_tail: list[Any] = []
    for m in tail:
        if _is_tool(m):
            tcid = getattr(m, "tool_call_id", None)
            if isinstance(tcid, str) and tcid in parent_ids:
                pruned_tail.append(m)
            else:
                continue
        else:
            pruned_tail.append(m)

    return systems + first_user + pruned_tail


__all__ = ["prune_messages"]


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

from collections.abc import Callable, Iterable, Sequence
from typing import Any

# Optional tokenizer support (tiktoken). Import lazily to avoid hard dependency.
_Tokenizer = Any  # alias for readability

def _get_tokenizer() -> _Tokenizer | None:
    """Return a tokenizer compatible with OpenAI 200k windows if available.

    We use tiktoken's ``o200k_base`` when installed. If unavailable, return None
    and higher-level callers should treat token-aware truncation as a no-op.
    """
    try:  # local import to keep import-time light when tiktoken isn't installed
        import tiktoken  # type: ignore

        try:
            return tiktoken.get_encoding("o200k_base")
        except Exception:
            # Older/newer tiktoken may raise; gracefully disable feature
            return None
    except Exception:
        return None


def _decode(tokenizer: _Tokenizer, ids: Sequence[int]) -> str:
    try:
        return tokenizer.decode(list(ids))  # type: ignore[attr-defined]
    except Exception:
        # Extremely defensive: if decode fails, drop tokens rather than crash
        return ""


def _encode(tokenizer: _Tokenizer, text: str) -> list[int]:
    try:
        return list(tokenizer.encode(text, disallowed_special=()))  # type: ignore[attr-defined]
    except Exception:
        return []


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

    # If no tool messages survived but the conversation contains a recent
    # assistant→tool pair, salvage the most recent pair to preserve coherence.
    if not any(_is_tool(m) for m in pruned_tail):
        try:
            # Find most recent tool message and its parent assistant in the core
            salvage_tool = None
            salvage_assistant = None
            for idx in range(len(core) - 1, -1, -1):
                m = core[idx]
                if _is_tool(m):
                    tcid = getattr(m, "tool_call_id", None)
                    if isinstance(tcid, str) and tcid:
                        # locate nearest preceding assistant with this tool id
                        for j in range(idx - 1, -1, -1):
                            a = core[j]
                            if _is_assistant(a) and tcid in _assistant_tool_call_ids(a):
                                salvage_tool = m
                                salvage_assistant = a
                                break
                if salvage_tool is not None:
                    break

            if salvage_tool is not None and salvage_assistant is not None:
                # Insert in chronological order if not already present
                if salvage_assistant not in pruned_tail:
                    pruned_tail.insert(0, salvage_assistant)
                if salvage_tool not in pruned_tail:
                    pruned_tail.insert(1 if pruned_tail and pruned_tail[0] is salvage_assistant else 0, salvage_tool)
        except Exception:
            pass

    return systems + first_user + pruned_tail


def truncate_message_tokens(
    msg: Any,
    max_tokens: int,
    tokenizer: _Tokenizer | None = None,
    *,
    marker_fmt: Callable[[int], str] | None = None,
) -> Any:
    """Return a message with content truncated to ``max_tokens`` if needed.

    - Operates on ``role in {"user", "assistant"}`` only; returns other roles unchanged.
    - Supports string ``content`` and list-of-chunks (with ``type`` of "text" or
      "reasoning"). Non-text chunks are preserved as-is and don't consume budget.
    - Preserves the message object shape; modifies content in-place when safe,
      otherwise returns a shallow copy with updated content.
    - If ``tokenizer`` is None or invalid, returns the input message unchanged.
    """
    role = getattr(msg, "role", None)
    if role not in ("user", "assistant"):
        return msg

    if max_tokens is None or max_tokens <= 0:
        return msg

    tok = tokenizer or _get_tokenizer()
    if tok is None:
        return msg

    # Marker function
    def _marker(trimmed: int) -> str:
        return f"\n...[+{trimmed} tokens trimmed]...\n"

    marker = marker_fmt or _marker

    # Helper: truncate a single string by tokens
    def _truncate_string(s: str, cap: int) -> tuple[str, int]:
        ids = _encode(tok, s)
        n = len(ids)
        if n <= cap:
            return s, 0
        trimmed = max(0, n - cap)
        m_str = marker(trimmed)
        # Reserve room for marker tokens so output is <= cap tokens (approximate)
        m_ids = _encode(tok, m_str)
        m_len = len(m_ids)
        avail = max(1, cap - m_len)
        head = max(1, avail // 2)
        tail = max(1, avail - head)
        out = _decode(tok, ids[:head]) + m_str + _decode(tok, ids[-tail:])
        return out, trimmed

    content = getattr(msg, "content", None)

    # Case 1: simple string content
    if isinstance(content, str):
        new_text, _ = _truncate_string(content, int(max_tokens))
        try:
            msg.content = new_text
            return msg
        except Exception:
            # Fallback to shallow copy if object is frozen
            new = getattr(msg, "__class__", object)()
            try:
                for k, v in msg.__dict__.items():
                    setattr(new, k, v)
                setattr(new, "content", new_text)
                return new
            except Exception:
                return msg

    # Case 2: list-of-chunks content (text/reasoning)
    if isinstance(content, list):
        # Collect token counts for text-bearing chunks
        token_lists: list[list[int]] = []
        token_counts: list[int] = []
        kinds: list[str] = []
        for item in content:
            # Support dict or object styles
            typ = None
            text_val = None
            try:
                typ = (item.get("type") if isinstance(item, dict) else getattr(item, "type", None))
            except Exception:
                typ = None
            if typ == "text":
                text_val = item.get("text") if isinstance(item, dict) else getattr(item, "text", "")
            elif typ == "reasoning":
                text_val = (
                    item.get("reasoning") if isinstance(item, dict) else getattr(item, "reasoning", "")
                )
            if typ in ("text", "reasoning") and isinstance(text_val, str):
                ids = _encode(tok, text_val)
                token_lists.append(ids)
                token_counts.append(len(ids))
                kinds.append(typ)
            else:
                token_lists.append([])
                token_counts.append(0)
                kinds.append("other")

        total = sum(token_counts)
        if total == 0:
            return msg

        cap = int(max_tokens)

        # Proportional allocation with minimum 1 for non-empty chunks
        # First pass: floating shares
        shares = [0] * len(token_counts)
        remaining = cap
        # Compute base shares via floor division
        remainders: list[tuple[float, int]] = []  # (remainder_frac, idx)
        for i, count in enumerate(token_counts):
            if count <= 0:
                shares[i] = 0
                continue
            raw = count * cap / max(1, total)
            base = int(raw)
            if base == 0:
                base = 1
            shares[i] = min(base, count)
            remaining -= shares[i]
            remainders.append((raw - base, i))

        # Distribute leftover (positive or negative)
        if remaining > 0:
            # Give to largest remainders without exceeding original counts
            for _, idx in sorted(remainders, reverse=True):
                if token_counts[idx] > shares[idx] and remaining > 0:
                    shares[idx] += 1
                    remaining -= 1
                    if remaining == 0:
                        break
        elif remaining < 0:
            # Remove from largest shares first
            for _, idx in sorted(remainders):
                if shares[idx] > 1 and remaining < 0:
                    dec = min(shares[idx] - 1, -remaining)
                    shares[idx] -= dec
                    remaining += dec
                    if remaining == 0:
                        break

        # Apply truncation per chunk
        trimmed_total = 0
        new_content: list[Any] = []
        for item, ids, count, share, kind in zip(content, token_lists, token_counts, shares, kinds):
            if kind in ("text", "reasoning") and count > share >= 0:
                text_val = item.get("text") if isinstance(item, dict) else getattr(item, "text", None)
                if kind == "reasoning":
                    text_val = (
                        item.get("reasoning") if isinstance(item, dict) else getattr(item, "reasoning", None)
                    )
                new_text, trimmed = _truncate_string(str(text_val or ""), share)
                trimmed_total += trimmed
                # write back preserving structure
                if isinstance(item, dict):
                    item = dict(item)  # shallow copy
                    if kind == "text":
                        item["text"] = new_text
                    else:
                        item["reasoning"] = new_text
                else:
                    try:
                        if kind == "text":
                            setattr(item, "text", new_text)
                        else:
                            setattr(item, "reasoning", new_text)
                    except Exception:
                        pass
                new_content.append(item)
            else:
                new_content.append(item)

        try:
            msg.content = new_content
        except Exception:
            pass
        return msg

    return msg


def truncate_conversation_tokens(
    messages: list[Any],
    max_tokens_per_msg: int,
    *,
    last_k: int = 200,
    tokenizer: _Tokenizer | None = None,
) -> list[Any]:
    """Apply per-message token caps to the tail of a conversation.

    - Only truncates ``role in {"user", "assistant"}``.
    - Leaves ``tool`` and ``system`` messages untouched.
    - Operates on the last ``last_k`` eligible messages to limit cost.
    - If no tokenizer is available, returns the original list unmodified.
    """
    if max_tokens_per_msg is None or max_tokens_per_msg <= 0:
        return messages

    tok = tokenizer or _get_tokenizer()
    if tok is None:
        return messages

    # Identify indices of eligible messages (assistant/user)
    eligible_indices: list[int] = [
        i for i in range(len(messages)) if getattr(messages[i], "role", None) in ("assistant", "user")
    ]
    # Work on last K eligible
    to_process = set(eligible_indices[-max(0, int(last_k)) :])

    # Shallow copy list; modify messages in place (objects mutated via helper)
    out = list(messages)
    for i in range(len(out)):
        if i in to_process:
            try:
                out[i] = truncate_message_tokens(out[i], int(max_tokens_per_msg), tok)
            except Exception:
                # Best-effort: skip problematic message rather than fail
                pass
    return out


__all__ = [
    "prune_messages",
    "truncate_message_tokens",
    "truncate_conversation_tokens",
]

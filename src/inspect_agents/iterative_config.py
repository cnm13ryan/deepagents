"""Pure helpers for iterative agent configuration resolution.

These functions centralize the precedence rules for environment variables vs.
explicit arguments. They do not perform any I/O other than reading os.environ
and contain no side effects, making them straightforward to unit test.
"""

from __future__ import annotations

import os


def _parse_int_opt(v: str | None) -> int | None:
    try:
        if v is None or str(v).strip() == "":
            return None
        iv = int(str(v).strip())
        return iv if iv > 0 else None
    except Exception:
        return None


def resolve_time_and_step_limits(
    *,
    real_time_limit_sec: int | None,
    max_steps: int | None,
) -> tuple[int | None, int | None]:
    """Return (time_limit, max_steps) with args > env precedence.

    - time limit env: ``INSPECT_ITERATIVE_TIME_LIMIT`` (seconds); non‑positive → None
    - step limit env: ``INSPECT_ITERATIVE_MAX_STEPS``; non‑positive → None
    """
    # Time limit
    time_limit: int | None = real_time_limit_sec
    if time_limit is None:
        try:
            time_limit = _parse_int_opt(os.getenv("INSPECT_ITERATIVE_TIME_LIMIT"))
        except Exception:
            time_limit = None

    # Step limit
    step_limit: int | None = max_steps
    if step_limit is None:
        try:
            step_limit = _parse_int_opt(os.getenv("INSPECT_ITERATIVE_MAX_STEPS"))
        except Exception:
            step_limit = None

    return time_limit, step_limit


def resolve_pruning(
    *,
    prune_after_messages: int | None,
    prune_keep_last: int,
) -> tuple[int | None, int]:
    """Return (prune_after, keep_last) honoring env overrides.

    Env precedence mirrors existing behavior:
    - ``INSPECT_PRUNE_AFTER_MESSAGES`` applies only when ``prune_after_messages``
      is None or the default (120). Non‑positive disables (None).
    - ``INSPECT_PRUNE_KEEP_LAST`` applies only when ``prune_keep_last`` equals
      the default (40). Negative values are clamped to 0.
    """
    eff_after: int | None = prune_after_messages
    eff_keep: int = prune_keep_last

    try:
        if prune_after_messages is None or prune_after_messages == 120:
            env_after = os.getenv("INSPECT_PRUNE_AFTER_MESSAGES")
            if env_after is not None and str(env_after).strip() != "":
                try:
                    v = int(env_after)
                    eff_after = v if v > 0 else None
                except Exception:
                    pass
    except Exception:
        pass

    try:
        if prune_keep_last == 40:
            env_keep = os.getenv("INSPECT_PRUNE_KEEP_LAST")
            if env_keep is not None and str(env_keep).strip() != "":
                try:
                    v = int(env_keep)
                    eff_keep = max(0, v)
                except Exception:
                    pass
    except Exception:
        pass

    return eff_after, eff_keep


def resolve_truncation(
    *,
    per_msg_token_cap: int | None,
    truncate_last_k: int,
) -> tuple[int | None, int]:
    """Return (per_msg_token_cap, last_k) honoring env overrides.

    - ``INSPECT_PER_MSG_TOKEN_CAP`` fills ``per_msg_token_cap`` only when arg is None.
    - ``INSPECT_TRUNCATE_LAST_K`` overrides ``truncate_last_k`` when set and > 0.
    """
    eff_cap: int | None = per_msg_token_cap
    if eff_cap is None:
        eff_cap = _parse_int_opt(os.getenv("INSPECT_PER_MSG_TOKEN_CAP"))

    eff_last_k: int = truncate_last_k
    try:
        env_last_k = _parse_int_opt(os.getenv("INSPECT_TRUNCATE_LAST_K"))
        if env_last_k is not None:
            eff_last_k = int(env_last_k)
    except Exception:
        pass

    return eff_cap, eff_last_k


__all__ = [
    "resolve_time_and_step_limits",
    "resolve_pruning",
    "resolve_truncation",
]


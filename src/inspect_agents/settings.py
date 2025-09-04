"""Centralized environment/settings utilities for inspect_agents.

Semantics mirror existing helpers to avoid regressions:
- truthy: case-insensitive membership in {"1","true","yes","on"}.
- default_tool_timeout: float from INSPECT_AGENTS_TOOL_TIMEOUT (fallback 15.0).
- typed_results_enabled: truthy(INSPECT_AGENTS_TYPED_RESULTS).
- int_env: parse int with optional min/max clamping; default on errors.
- float_env: parse float; default on errors.
- str_env: passthrough string (or default/None when unset).
"""

from __future__ import annotations

import os


def truthy(val: str | None) -> bool:
    """Return True for common truthy string values.

    Accepts: "1", "true", "yes", "on" (case-insensitive). None -> False.
    """
    if val is None:
        return False
    return val.strip().lower() in {"1", "true", "yes", "on"}


def int_env(name: str, default: int, minimum: int | None = None, maximum: int | None = None) -> int:
    """Read an integer env var with optional clamping and safe fallback.

    - Returns `default` on parse errors or when unset.
    - Applies `minimum`/`maximum` clamps when provided.
    """
    raw = os.getenv(name)
    try:
        val = int(raw) if raw is not None and str(raw).strip() != "" else int(default)
    except Exception:
        val = int(default)
    if minimum is not None:
        val = max(minimum, val)
    if maximum is not None:
        val = min(maximum, val)
    return val


def float_env(name: str, default: float) -> float:
    """Read a float env var; return `default` on errors or when unset."""
    raw = os.getenv(name)
    try:
        return float(raw) if raw is not None and str(raw).strip() != "" else float(default)
    except Exception:
        return float(default)


def str_env(name: str, default: str | None = None) -> str | None:
    """Read a string env var; return `default` when unset."""
    val = os.getenv(name)
    return default if val is None else val


def typed_results_enabled() -> bool:
    """Whether typed result models should be returned by tools."""
    return truthy(os.getenv("INSPECT_AGENTS_TYPED_RESULTS"))


def default_tool_timeout() -> float:
    """Default tool timeout (seconds). Env: INSPECT_AGENTS_TOOL_TIMEOUT (float)."""
    return float_env("INSPECT_AGENTS_TOOL_TIMEOUT", 15.0)


__all__ = [
    "truthy",
    "int_env",
    "float_env",
    "str_env",
    "typed_results_enabled",
    "default_tool_timeout",
]

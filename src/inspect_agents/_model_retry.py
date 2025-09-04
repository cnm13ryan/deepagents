"""Model generate() retry wrapper that tracks planned backoff time.

This module provides a small shim around Inspect-AI models' `generate(...)`
that (a) retries on transient failures using tenacity and (b) sums the
upcoming sleep/backoff that tenacity schedules so callers can subtract that
from a time budget ("productive time" accounting).

Design goals:
- No changes to Inspect internals; purely optional wrapper for callers.
- Degrades gracefully if `tenacity` isn't available (falls back to a
  simple fixed backoff loop with the same accounting semantics).
- Retry predicate is conservative and provider-agnostic.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable
from typing import Any

# Optional imports to avoid hard dependency at import time
try:  # pragma: no cover - exercised in runtime, but defensive import
    from tenacity import (
        RetryCallState,
        retry,
        retry_if_exception,
        stop_after_attempt,
        wait_exponential_jitter,
    )
    _TENACITY_AVAILABLE = True
except Exception:  # pragma: no cover
    RetryCallState = object  # type: ignore
    _TENACITY_AVAILABLE = False


class RetryableGenerateError(RuntimeError):
    """Lightweight exception for tests/providers to signal retryable failures."""


def _bool_env(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    s = str(v).strip().lower()
    return s in {"1", "true", "yes", "on"}


def _float_env(name: str, default: float) -> float:
    try:
        v = os.getenv(name)
        if v is None or str(v).strip() == "":
            return default
        return float(v)  # may raise
    except Exception:
        return default


def _int_env(name: str, default: int) -> int:
    try:
        v = os.getenv(name)
        if v is None or str(v).strip() == "":
            return default
        return int(v)  # may raise
    except Exception:
        return default


def _default_retry_predicate(ex: BaseException) -> bool:
    """Best-effort classification of retryable errors across providers.

    - Retry our explicit `RetryableGenerateError` used by tests.
    - Retry `TimeoutError`/`asyncio.TimeoutError`.
    - Retry on exceptions exposing an HTTP `status_code` that is 429 or 5xx.
    - Retry generic transient I/O like `OSError` (network hiccups).
    - If httpx is importable, treat its network errors as retryable.
    """

    if isinstance(ex, RetryableGenerateError):
        return True

    if isinstance(ex, (TimeoutError, asyncio.TimeoutError, OSError)):
        return True

    # Heuristic: common HTTP-style attributes
    status = getattr(ex, "status_code", None)
    try:
        if isinstance(status, int) and (status == 429 or 500 <= status < 600):
            return True
    except Exception:
        pass

    try:  # pragma: no cover - only exercised when httpx is present
        import httpx  # type: ignore

        if isinstance(ex, (
            httpx.ConnectError,
            httpx.ReadError,
            httpx.WriteError,
            httpx.ReadTimeout,
            httpx.ConnectTimeout,
            httpx.RemoteProtocolError,
            httpx.NetworkError,
        )):
            return True
    except Exception:
        pass

    return False


async def _call_generate(
    model: Any,
    *,
    input: list[Any],
    tools: list[object],
    cache: bool,
    config: Any,
) -> Any:
    return await model.generate(input=input, tools=tools, cache=cache, config=config)


async def generate_with_retry_time(
    model: Any,
    *,
    input: list[Any],
    tools: list[object],
    cache: bool,
    config: Any,
    # Optional knobs via env (provide as args if needed in future)
    retry_predicate: Callable[[BaseException], bool] | None = None,
) -> tuple[Any, float]:
    """Call `model.generate(...)` with retries and report backoff time.

    Returns a tuple of (output, retry_sleep_seconds_accumulated).

    Behavior is controlled by env vars:
    - INSPECT_RETRY_MAX_ATTEMPTS: max attempts including the first (default 6)
    - INSPECT_RETRY_INITIAL_SECONDS: initial backoff (default 1.0)
    - INSPECT_RETRY_MAX_SECONDS: cap on backoff (default 60.0)
    - INSPECT_RETRY_JITTER: if >0 enables jitter range in seconds (default 0)

    This wrapper is always safe to use even when you choose not to subtract the
    returned backoff time from your loop accounting.
    """

    max_attempts = max(1, _int_env("INSPECT_RETRY_MAX_ATTEMPTS", 6))
    initial = max(0.0, _float_env("INSPECT_RETRY_INITIAL_SECONDS", 1.0))
    wait_max = max(initial, _float_env("INSPECT_RETRY_MAX_SECONDS", 60.0))
    jitter = max(0.0, _float_env("INSPECT_RETRY_JITTER", 0.0))

    pred = retry_predicate or _default_retry_predicate
    retry_sleep_total = 0.0

    # Tenacity path with before_sleep accumulation
    if _TENACITY_AVAILABLE:
        upcoming: dict[str, float] = {"sleep": 0.0}

        async def _before_sleep(state: RetryCallState) -> None:  # type: ignore[override]
            try:
                # tenacity exposes `upcoming_sleep` on the state
                s = float(getattr(state, "upcoming_sleep", 0.0) or 0.0)
            except Exception:
                s = 0.0
            upcoming["sleep"] += s

        @retry(
            wait=wait_exponential_jitter(initial=initial, max=wait_max, jitter=jitter),
            stop=stop_after_attempt(max_attempts),
            retry=retry_if_exception(pred),
            before_sleep=_before_sleep,
        )
        async def _call() -> Any:
            return await _call_generate(
                model, input=input, tools=tools, cache=cache, config=config
            )

        out = await _call()
        retry_sleep_total = float(upcoming["sleep"])  # seconds
        return out, retry_sleep_total

    # Fallback: no tenacity available, emulate a basic fixed-exponential backoff
    attempts = 0
    delay = initial
    last_exc: BaseException | None = None
    while attempts < max_attempts:
        try:
            return (
                await _call_generate(model, input=input, tools=tools, cache=cache, config=config),
                float(retry_sleep_total),
            )
        except BaseException as ex:  # pragma: no cover - exercised only w/o tenacity
            last_exc = ex
            if not pred(ex) or attempts + 1 >= max_attempts:
                raise
            await asyncio.sleep(delay)
            retry_sleep_total += float(delay)
            delay = min(wait_max, max(initial, delay * 2.0))
            attempts += 1

    # Should not reach here; re-raise last
    assert last_exc is not None
    raise last_exc


__all__ = ["generate_with_retry_time", "RetryableGenerateError"]


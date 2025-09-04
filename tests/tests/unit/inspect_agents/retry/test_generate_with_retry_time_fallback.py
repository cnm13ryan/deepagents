# test(retry): cover fallback path and non-retryable behavior

import importlib
import types

import pytest


class _FlakyModel:
    def __init__(self, fails=2):
        self._n = int(fails)

    async def generate(self, *, input, tools, cache, config):  # noqa: D401
        if self._n > 0:
            self._n -= 1
            raise TimeoutError("retryable")
        # minimal result with a .message attribute
        return types.SimpleNamespace(message=types.SimpleNamespace(content="ok"))


@pytest.mark.asyncio
async def test_retry_fallback_accumulates_sleep(monkeypatch):
    # Force fallback path (pretend Tenacity not available)
    mod = importlib.import_module("inspect_agents._model_retry")
    monkeypatch.setattr(mod, "_TENACITY_AVAILABLE", False, raising=True)

    # Fast retry budget
    monkeypatch.setenv("INSPECT_RETRY_MAX_ATTEMPTS", "3")
    monkeypatch.setenv("INSPECT_RETRY_INITIAL_SECONDS", "0.01")
    monkeypatch.setenv("INSPECT_RETRY_MAX_SECONDS", "0.02")

    from inspect_agents._model_retry import generate_with_retry_time

    model = _FlakyModel(fails=2)
    out, sleep_s = await generate_with_retry_time(
        model, input=[], tools=[], cache=False, config=None
    )
    assert getattr(out, "message", None) is not None
    assert sleep_s >= 0.01  # at least one backoff step counted


@pytest.mark.asyncio
async def test_retry_fallback_non_retryable_raises(monkeypatch):
    mod = importlib.import_module("inspect_agents._model_retry")
    monkeypatch.setattr(mod, "_TENACITY_AVAILABLE", False, raising=True)

    class BadModel:
        async def generate(self, *, input, tools, cache, config):
            raise ValueError("non-retryable")

    from inspect_agents._model_retry import generate_with_retry_time

    with pytest.raises(ValueError):
        await generate_with_retry_time(BadModel(), input=[], tools=[], cache=False, config=None)


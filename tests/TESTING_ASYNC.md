# Testing Guide — Async (pytest-asyncio)

Use `pytest-asyncio` for native async tests and event-loop fixtures.

## Defaults in this repo
- Loop scope: `asyncio_default_fixture_loop_scope = "function"` to isolate loops per test.
- Prefer `@pytest.mark.asyncio` for async tests; avoid custom loop fixtures unless required.

## Patterns
- Mark test coroutine:
  ```python
  import pytest

  @pytest.mark.asyncio
  async def test_async_behavior():
      # arrange/act/assert
      ...
  ```
- Async helpers: call `await` against functions under test; avoid `asyncio.run()` inside async tests (ok in sync tests).

## Timeouts and cancellation
- Use `anyio.fail_after(..)` or `anyio.move_on_after(..)` to bound ops; assert timeout surfaces as error where appropriate (see tool timeouts tests).

## Fixtures
- Use `monkeypatch` to set env flags for deterministic async behavior (e.g., `NO_NETWORK`, sandbox toggles).
- Keep side effects scoped to each test and undo via `monkeypatch.delenv` when needed.

## Gotchas
- Avoid sharing async clients/resources across tests without explicit fixture scoping.
- Don’t block the loop with CPU-bound work; offload to threads if necessary.

## References
- pytest-asyncio usage and markers.

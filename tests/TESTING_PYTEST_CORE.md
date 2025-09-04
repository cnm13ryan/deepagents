# Testing Guide — Pytest Core

This repo uses pytest as the primary test runner. Tests live under `tests/` and default to an offline, deterministic configuration.

## Conventions
- Structure: keep tests close to features (e.g., `tests/integration/inspect_agents/`).
- Naming: `test_*.py`, functions `test_*` with clear, behavior-based names.
- Imports: prefer local module imports inside tests to minimize import cost and cross-test state.
- Offline by default: set `NO_NETWORK=1` for all tests unless a test explicitly proves online behavior.
- Determinism: avoid time- and randomness-dependent assertions; seed or pin where needed.

## Running
- Fast subset: `uv run pytest -q -k <expr>`
- Full suite: `CI=1 NO_NETWORK=1 uv run pytest -q`
- Show markers: `pytest --markers`

## Fixtures and Scope
- Use fixtures to arrange stable state; prefer function scope unless a larger scope is justified.
- Autouse fixtures only when every test in the module needs them; otherwise request explicitly.
- Don’t rely on fixture definition order; use explicit dependencies for ordering.
  See pytest fixture docs on scopes and ordering.

## Parametrization and Markers
- Prefer `@pytest.mark.parametrize` over ad-hoc loops in tests.
- Use markers to group/select tests (`-m <expr>`); register custom markers in config if needed.

## Async tests
- This repo sets `asyncio_default_fixture_loop_scope = "function"` to keep event loops isolated between tests.
- Use `@pytest.mark.asyncio` for native async tests; avoid custom `event_loop` fixtures (modern guidance).

## Warnings and Filters
- Central filters live in pyproject to keep noise down and preserve signal.

## Selection and Bisection
- Use `-k` to narrow to filenames/patterns quickly.
- When isolating pollution, grow subsets alphabetically (e.g., `-k iterative`, `test_[a-f]*`).

## Style
- Assertions: single, specific invariant per test; multiple related asserts are fine.
- Keep helpers small; promote shared helpers to fixtures when reused ≥3 times.

## References
- Pytest docs: fixtures, parametrization, markers.

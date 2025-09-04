# Testing Guide — Parallel Execution (xdist)

Use `pytest-xdist` to parallelize where safe, and avoid shared global state.

## Running
- Auto-parallel: `pytest -q -n auto`
- Explicit workers: `pytest -q -n 4`

## Design for safety
- Tests must be order- and process-independent; avoid writes to the same temp path.
- Avoid global singletons; prefer per-test stores/fixtures.
- For stateful subsystems (e.g., approvals, env toggles), scope with `monkeypatch` and clear between tests.

## When to avoid xdist
- Tests that rely on process-global mocks shims without isolation.
- Tests that intentionally serialize heavy resources.

## References
- pytest-xdist docs (overview and usage).

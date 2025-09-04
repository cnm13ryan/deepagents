# Tests: Inspect-AI Source of Truth

This repository’s tests must target the installed site‑packages version of
`inspect_ai`. The copy under `external/inspect_ai/` is reference‑only (for
browsing, diffs, and local development) and must not be imported or placed on
`sys.path` by tests.

Why: keeping tests bound to the installed package prevents version skew and
ensures we validate against the exact dependency surface that users get via
`pip/uv`.

## Do / Don’t

Do:
- Import Inspect‑AI symbols from the installed package, e.g. `from inspect_ai.tool._tool_call import ToolCall`.
- Use Inspect’s public helpers (e.g., `policy_approver(...)`) to exercise
  behavior without re‑implementing approvals.
- If you must stub Inspect modules for a unit test, scope stubs inside a helper
  and clean them up in `teardown_module` (delete any stubbed `sys.modules[...]`
  entries).
- Keep tests deterministic and offline by default: set `CI=1` and
  `NO_NETWORK=1` when running locally or in CI.

Don’t:
- Add `external/inspect_ai/src` to `sys.path` (directly or via `PYTHONPATH`).
- Import from `external/inspect_ai/...` in tests.
- Leave global `sys.modules` shims in place after a test module finishes.
- Depend on private, unstable internals unless absolutely necessary.

## Running Tests

Installed‐package first:

- Ensure dependencies are installed (example with `uv`):
  - `uv sync`
- Run the whole suite offline and quiet:
  - `CI=1 NO_NETWORK=1 pytest -q -v`
- Run subsets while iterating:
  - `CI=1 NO_NETWORK=1 pytest -q -v tests/unit/inspect_agents -k '<expr>'`

Notes:
- The repository’s `tests/unit/inspect_agents/conftest.py` intentionally only
  adds the repo `src/` to `sys.path` and defers all `inspect_ai` imports to the
  installed package.
- If a test needs to simulate Inspect behavior, prefer calling
  `policy_approver(policies)` over importing internal approval runners. If a
  shim is unavoidable, register it inside the test module and remove it in
  `teardown_module`.

### Fixture: approval_modules_guard

Tests that temporarily stub `inspect_ai.approval*` modules should use the
shared fixture `approval_modules_guard` (from `tests/conftest.py`):

```
def test_something(approval_modules_guard):
    # install stubs into sys.modules["inspect_ai.approval._apply"], etc.
    ...
    # stubs are automatically cleaned up and originals restored on exit
```

The fixture snapshots any existing originals, and on teardown it restores them
or removes stub entries (only when clearly a stub, e.g. modules without
`__file__`). This prevents cross‑test contamination while keeping real imports
intact.

## Rationale & Footguns

- Mixing the vendored copy with the installed package leads to subtle type/schema
  mismatches (e.g., Pydantic models, dataclasses), so tests must never depend on
  the vendored path being importable.
- Cross‑test contamination via `sys.modules` is a common source of flaky
  failures. Keep any test‑local stubs narrow and short‑lived, and always clean
  them up in `teardown_module`.

# DeepAgents Test Guides

Central index of testing guides for this repository. Tests default to offline, fast, and deterministic runs.

## Guides
- Pytest core: `TESTING_PYTEST_CORE.md`
- Async tests (pytest-asyncio): `TESTING_ASYNC.md`
- Approvals & policies: `TESTING_APPROVALS_POLICIES.md`
- Subagents & handoffs: `TESTING_SUBAGENTS_HANDOFFS.md`
- Tools & filesystem: `TESTING_TOOLS_FILESYSTEM.md`
- Tool timeouts: `TESTING_TOOL_TIMEOUTS.md`
- Limits & truncation: `TESTING_LIMITS_TRUNCATION.md`
- Model resolution: `TESTING_MODEL_RESOLUTION.md`
- Coverage (pytest-cov/coverage.py): `TESTING_COVERAGE.md`
- Parallel (pytest-xdist): `TESTING_PARALLEL.md`
- Benchmarks (pytest-benchmark): `TESTING_BENCHMARKS.md`
- Property-based (Hypothesis): `TESTING_PROPERTY_BASED.md`
- Mocking (pytest-mock): `TESTING_MOCKING.md`

## Quick Commands
- Run all tests offline: `CI=1 NO_NETWORK=1 uv run pytest -q`
- Narrow to a subset: `uv run pytest -q -k <expr>`
- Parallel (safe suites only): `uv run pytest -q -n auto`

## Conventions
- Keep tests deterministic; set env in-tests via `monkeypatch`.
- Prefer small, behavior-focused tests; use fixtures for shared setup.

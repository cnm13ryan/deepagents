"""CI-friendly pytest hooks that surface testing guides on failures.

This prints a short pointer to repo-local testing guides when the test session
has failures, making it easy for contributors and CI logs to link to the
appropriate docs. It is intentionally lightweight and has zero effect on
outcomes or exit codes.

Behavior:
- Always include a one-line header pointing to tests/README.md.
- When failures occur, emit a small section with relevant guide file paths
  inferred from failing node ids (e.g., approvals, handoffs, timeouts,
  truncation, parallel, model resolution).
- Only activates in CI (CI=1) or when DEEPAGENTS_SHOW_TEST_GUIDES is truthy.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterable
from pathlib import Path

import pytest

# Ensure src/ (and optional external/inspect_ai) are importable for tests
# This avoids requiring an editable install in local runs/CI.
_TESTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_DIR.parent
_SRC = _REPO_ROOT / "src"
_EXT_INSPECT = _REPO_ROOT / "external" / "inspect_ai"
for _p in (_EXT_INSPECT, _SRC):
    try:
        if _p.exists():
            pstr = str(_p)
            if pstr not in sys.path:
                sys.path.insert(0, pstr)
    except Exception:
        # Never fail test collection due to path setup
        pass


def _truthy(v: str | None) -> bool:
    return bool(v) and str(v).strip().lower() in {"1", "true", "yes", "on"}


ROOT = Path(__file__).resolve().parent
GUIDE_INDEX = ROOT / "README.md"

GUIDES = {
    "approvals": ROOT / "TESTING_APPROVALS_POLICIES.md",
    "handoff": ROOT / "TESTING_SUBAGENTS_HANDOFFS.md",
    "subagent": ROOT / "TESTING_SUBAGENTS_HANDOFFS.md",
    "filters": ROOT / "TESTING_SUBAGENTS_HANDOFFS.md",
    "kill_switch": ROOT / "TESTING_APPROVALS_POLICIES.md",
    "timeout": ROOT / "TESTING_TOOL_TIMEOUTS.md",
    "tool_timeouts": ROOT / "TESTING_TOOL_TIMEOUTS.md",
    "truncation": ROOT / "TESTING_LIMITS_TRUNCATION.md",
    "parallel": ROOT / "TESTING_PARALLEL.md",
    "runner_model": ROOT / "TESTING_MODEL_RESOLUTION.md",
    "model_flags": ROOT / "TESTING_MODEL_RESOLUTION.md",
    "mock": ROOT / "TESTING_MOCKING.md",
    "benchmark": ROOT / "TESTING_BENCHMARKS.md",
    "async": ROOT / "TESTING_ASYNC.md",
}


def _guides_for_nodeid(nodeid: str) -> set[Path]:
    s = nodeid.lower()
    out: set[Path] = set()
    for key, path in GUIDES.items():
        if key in s:
            out.add(path)
    return out


# Capture markers during collection so we can map failures to guides precisely
_NODE_MARKS: dict[str, set[str]] = {}


def pytest_collection_modifyitems(items):  # pragma: no cover - wiring only
    for item in items:
        try:
            marks = {m.name for m in item.iter_markers()}
        except Exception:
            marks = set()
        _NODE_MARKS[item.nodeid] = marks


def pytest_report_header(config):  # pragma: no cover - cosmetic
    # One-line pointer at session start; always useful
    return [f"guides: {GUIDE_INDEX}"]


def _failed_reports(terminalreporter) -> Iterable[object]:
    try:
        return terminalreporter.stats.get("failed", [])
    except Exception:
        return []


def pytest_terminal_summary(terminalreporter, exitstatus, config):  # pragma: no cover - formatting only
    if not (_truthy(os.getenv("CI")) or _truthy(os.getenv("DEEPAGENTS_SHOW_TEST_GUIDES"))):
        return

    failed = list(_failed_reports(terminalreporter))
    if not failed:
        return

    guides: set[Path] = set()
    for rep in failed:
        nodeid = getattr(rep, "nodeid", "")
        # Prefer markers if present
        marks = _NODE_MARKS.get(nodeid, set())
        for m in marks:
            p = GUIDES.get(m)
            if p:
                guides.add(p)
        # Fallback to keyword heuristics
        if not marks:
            guides.update(_guides_for_nodeid(nodeid))

    # Always include the index
    # Prefer reporter API for broad compatibility with plugins
    try:
        terminalreporter.write_sep("=", "DeepAgents test guides")
    except Exception:
        terminalreporter.write_line("========== DeepAgents test guides ==========")
    terminalreporter.write_line(f"Index: {GUIDE_INDEX}")

    if guides:
        terminalreporter.write_line("Relevant:")
        for p in sorted(guides):
            terminalreporter.write_line(f"- {p}")
    else:
        terminalreporter.write_line("No specific match; see the index above.")

# ----------------------------------------------------------------------
# Optional plugin shims
# ----------------------------------------------------------------------

# Provide a minimal no-op 'benchmark' fixture when pytest-benchmark is absent.
# This keeps benchmark tests runnable in environments that don't install the
# optional plugin, treating them as functional smoke checks.
try:  # pragma: no cover - exercised only when plugin missing
    pass  # type: ignore
except Exception:  # pragma: no cover - simple shim
    import pytest

    @pytest.fixture
    def benchmark():
        def _runner(func, *args, **kwargs):
            if callable(func):
                return func(*args, **kwargs)
            return func
        return _runner

# Guard/cleanup fixture for approval-related tests that stub inspect_ai modules
# and register global approvers. Ensures isolation across tests.


@pytest.fixture
def approval_modules_guard():  # pragma: no cover - test support only
    import sys as _sys

    # Remember originals and clear stubs before running
    _mod_names = [
        'inspect_ai.approval._approval',
        'inspect_ai.approval._policy',
        'inspect_ai._util.registry',
        'inspect_ai.tool._tool_call',
    ]
    _saved = {name: _sys.modules.get(name) for name in _mod_names}
    for name in _mod_names:
        _sys.modules.pop(name, None)

    # Clear any registered approver
    try:
        from inspect_ai.approval._apply import init_tool_approval  # type: ignore
        init_tool_approval(None)  # type: ignore[func-returns-value]
    except Exception:
        pass

    try:
        yield
    finally:
        # Restore modules and clear approver again
        for name, mod in _saved.items():
            if mod is None:
                _sys.modules.pop(name, None)
            else:
                _sys.modules[name] = mod
        try:
            from inspect_ai.approval._apply import init_tool_approval  # type: ignore
            init_tool_approval(None)  # type: ignore[func-returns-value]
        except Exception:
            pass


# Minimal asyncio runner shim: if pytest-asyncio isn't installed, execute
# coroutine tests marked with @pytest.mark.asyncio using asyncio.run.
def pytest_pyfunc_call(pyfuncitem):  # pragma: no cover - passthrough logic
    import inspect as _inspect

    try:
        return None  # Defer to plugin if present
    except Exception:
        pass

    test_fn = pyfuncitem.obj
    if _inspect.iscoroutinefunction(test_fn):
        # Only handle when explicitly marked asyncio to avoid surprises
        if pyfuncitem.get_closest_marker("asyncio") is None:
            return None
        import asyncio as _asyncio
        # Build kwargs from resolved fixtures
        argnames = getattr(pyfuncitem._fixtureinfo, "argnames", ())
        kwargs = {name: pyfuncitem.funcargs[name] for name in argnames}
        _asyncio.run(test_fn(**kwargs))
        return True
    return None
# Optional dependency shims
# Provide a lightweight fallback stub for the optional `jsonlines` dependency
# used by Inspect‑AI trace/dataset utilities. This keeps tests offline‑friendly
# while still allowing import of Inspect‑AI internals that reference jsonlines.
try:  # pragma: no cover
    import jsonlines as _jsonlines  # type: ignore  # noqa: F401
except Exception:  # pragma: no cover
    import json
    import types as _types

    _jl = _types.ModuleType("jsonlines")

    class _Reader:
        def __init__(self, fp):
            self._fp = fp

        def iter(self, type=dict):  # noqa: A002 - match third‑party API
            for line in self._fp:
                try:
                    yield json.loads(line)
                except Exception:
                    continue

    _jl.Reader = _Reader  # type: ignore[attr-defined]
    sys.modules["jsonlines"] = _jl

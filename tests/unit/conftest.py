import sys
from pathlib import Path

# Ensure tests import local packages first:
# - project library: src/
# Use installed inspect_ai instead of external submodule to ensure dependencies are available
ROOT = Path(__file__).resolve().parents[1]
LOCAL_SRC = str(ROOT / "src")

if LOCAL_SRC not in sys.path:
    sys.path.insert(0, LOCAL_SRC)


def pytest_report_header(config):  # pragma: no cover
    # Show where inspect_ai resolves from for easy debugging
    try:
        import inspect_ai  # type: ignore

        return [f"inspect_ai={getattr(inspect_ai, '__file__', '?')}"]
    except Exception as e:  # if import fails, surface reason in header
        return [f"inspect_ai=IMPORT_FAILED: {type(e).__name__}: {e}"]

# Provide a lightweight fallback stub for the optional `jsonlines` dependency
# used by Inspect‑AI trace/dataset utilities. This keeps tests offline‑friendly
# while still allowing import of Inspect‑AI internals that reference jsonlines.
try:  # pragma: no cover
    import jsonlines  # type: ignore
except Exception:  # pragma: no cover
    import types, json

    stub = types.ModuleType("jsonlines")

    class _Reader:
        def __init__(self, fp):
            self._fp = fp

        def iter(self, type=dict):  # noqa: A002 - match third‑party API
            for line in self._fp:
                try:
                    yield json.loads(line)
                except Exception:
                    continue

    stub.Reader = _Reader  # type: ignore[attr-defined]
    sys.modules["jsonlines"] = stub

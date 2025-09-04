import sys
from pathlib import Path

import pytest

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
    pass  # type: ignore
except Exception:  # pragma: no cover
    import json
    import types

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


# ---- Shared fixtures ----

@pytest.fixture
def approval_modules_guard():
    """Guard and restore inspect_ai.approval* sys.modules entries.

    Use in tests that stub any of:
      - inspect_ai.approval._apply
      - inspect_ai.approval._policy
      - inspect_ai.approval._approval

    Behavior:
    - Snapshot originals on entry.
    - On exit, restore originals if they existed.
    - If there was no original and a stub (module without __file__) was added,
      remove that stub entry; leave real imports intact.
    """

    keys = (
        "inspect_ai.approval._apply",
        "inspect_ai.approval._policy",
        "inspect_ai.approval._approval",
    )

    originals: dict[str, object | None] = {k: sys.modules.get(k) for k in keys}

    try:
        yield
    finally:
        for k, orig in originals.items():
            cur = sys.modules.get(k)
            if orig is not None:
                # Restore the exact original module object
                sys.modules[k] = orig
            else:
                # No original existed; remove only obvious stubs (no __file__)
                if cur is not None and getattr(cur, "__file__", None) is None:
                    sys.modules.pop(k, None)

"""Integration test bootstrap + offline hardening.

Behavior:
- Ensure repo `src/` is importable and prefer the installed `inspect_ai`.
- Apply a per-test hardening fixture to neutralize environment leakage that can
  cause hangs in offline smoke tests:
    * Clear any globally-registered approvals (best-effort).
    * Disable optional standard tools (web_search/exec/browser/editor).
    * Unset common web search provider keys so auto-enable paths don’t trigger.

Individual tests can still override these via their own `monkeypatch` calls.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


@pytest.fixture(autouse=True)
def _offline_env_hardening(monkeypatch):
    """Neutralize approvals and heavy optional tools before each test.

    This reduces flakiness/hangs when developers run subsets interactively with
    prior global approvals or provider keys in the shell.
    """
    # Best-effort: clear any previously-registered approvals
    try:  # pragma: no cover - shim may not exist in all environments
        from inspect_ai.approval._apply import init_tool_approval  # type: ignore

        init_tool_approval(None)  # type: ignore[func-returns-value]
    except Exception:
        pass

    # Disable optional tools to keep supervisor init deterministic
    monkeypatch.setenv("INSPECT_ENABLE_WEB_SEARCH", "0")
    monkeypatch.setenv("INSPECT_ENABLE_EXEC", "0")
    monkeypatch.setenv("INSPECT_ENABLE_WEB_BROWSER", "0")
    monkeypatch.setenv("INSPECT_ENABLE_TEXT_EDITOR_TOOL", "0")

    # Unset provider keys that would auto-enable web_search
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_CSE_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CSE_API_KEY", raising=False)

    # Ensure no network by default for integration-offline scope (tests can override)
    if not Path(REPO_ROOT / ".allow_network_in_tests").exists():  # escape hatch if needed
        monkeypatch.setenv("NO_NETWORK", "1")

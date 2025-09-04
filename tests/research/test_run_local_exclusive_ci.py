import asyncio
import importlib.util
from pathlib import Path


def _load_run_local_module():
    path = Path(__file__).resolve().parents[2] / "examples" / "research" / "run_local.py"
    spec = importlib.util.spec_from_file_location("run_local_ci", str(path))
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def test_ci_appends_handoff_exclusive_policy(monkeypatch, tmp_path):
    # Arrange: ensure offline-friendly env
    monkeypatch.setenv("CI", "1")
    monkeypatch.setenv("NO_NETWORK", "1")
    monkeypatch.setenv("INSPECT_LOG_DIR", str(tmp_path))

    # Capture approvals passed to run_agent
    captured: dict[str, object] = {}

    async def fake_run_agent(agent, user_input, approval=None, limits=None, **kwargs):  # noqa: ANN001, D401
        captured["approval"] = approval
        # Minimal result-like object with .output.completion
        class _Out:
            completion = "ok"

        class _Res:
            output = _Out()

        return _Res()

    # Patch inspect_agents hooks used by the runner
    import inspect_agents.approval as approval_mod

    monkeypatch.setattr(
        approval_mod,
        "handoff_exclusive_policy",
        lambda: ["EXCLUSIVE_SENTINEL"],
        raising=True,
    )

    # Keep approval_preset light to avoid unrelated policies in the assertion
    monkeypatch.setattr(approval_mod, "approval_preset", lambda preset: [], raising=True)

    import inspect_agents.run as run_mod
    monkeypatch.setattr(run_mod, "run_agent", fake_run_agent, raising=True)

    # Load the runner module and invoke _main with --approval ci
    run_local = _load_run_local_module()

    argv = [
        "run_local.py",
        "Quick check",
        "--approval",
        "ci",
    ]

    monkeypatch.setattr("sys.argv", argv, raising=False)

    # Act
    rc = asyncio.run(run_local._main())

    # Assert
    assert rc == 0
    approval = captured.get("approval")
    assert isinstance(approval, list)
    assert "EXCLUSIVE_SENTINEL" in approval, "handoff_exclusive_policy() not applied for ci"

import os
import sys
import subprocess
from pathlib import Path


def _repo_root(start: Path) -> Path:
    cur = start
    for _ in range(6):  # search upward a few levels
        if (cur / "pyproject.toml").exists():
            return cur
        cur = cur.parent
    # Fallback to two parents up
    return start.parents[2]


def _env_with_paths(repo: Path) -> dict:
    env = os.environ.copy()
    # Ensure local sources resolve in subprocess
    src = str(repo / "src")
    ext = str(repo / "external" / "inspect_ai")
    sep = os.pathsep
    env["PYTHONPATH"] = sep.join(filter(None, [src, ext, env.get("PYTHONPATH", "")]))
    env["DEEPAGENTS_TEST_ECHO_MODEL"] = "1"
    env.setdefault("NO_NETWORK", "1")
    env.setdefault("CI", "1")
    return env


def _run(cmd, cwd: Path, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True)


def test_run_local_explicit_provider_and_model_echoes_prefixed_model():
    repo = _repo_root(Path(__file__).resolve())
    script = repo / "examples" / "research" / "run_local.py"
    env = _env_with_paths(repo)
    # Bare model name + provider should resolve to provider/model
    proc = _run([sys.executable, str(script), "--provider", "ollama", "--model", "llama3.1", "noop"], cwd=repo, env=env)
    assert proc.returncode == 0, proc.stderr
    # First line should be the echoed model id
    first_line = (proc.stdout or "").strip().splitlines()[0]
    assert first_line == "ollama/llama3.1"


def test_run_iterative_explicit_model_passthrough():
    repo = _repo_root(Path(__file__).resolve())
    script = repo / "examples" / "research" / "run_iterative.py"
    env = _env_with_paths(repo)
    # Fully-qualified model should pass through unchanged
    proc = _run([sys.executable, str(script), "--model", "openai/gpt-4o-mini", "noop"], cwd=repo, env=env)
    assert proc.returncode == 0, proc.stderr
    first_line = (proc.stdout or "").strip().splitlines()[0]
    assert first_line == "openai/gpt-4o-mini"


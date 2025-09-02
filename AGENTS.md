# Repository Guidelines

## Project Structure & Module Organization
- `src/inspect_agents/`: Inspect‑AI–native library (agents, tools, state, config).
- `tests/inspect_agents/`: Pytest suite for library behavior and shims.
- `examples/inspect/`: CLI demos (`prompt_task.py`, `run.py`).
- `env_templates/`: Example env file (`inspect.env`).
- `external/inspect_ai/`: Inspect‑AI source (submodule/checkout for local dev).
- `.inspect/logs/` and `logs/`: Runtime transcripts and traces.

## Build, Test, and Development Commands
- Install: `uv sync` (or `python3.11 -m venv .venv && pip install -e .`).
- Run CLI task: `uv run inspect eval examples/inspect/prompt_task.py -T prompt="..."`.
- Run Python runner: `uv run python examples/inspect/run.py "..."`.
- Test fast: `CI=1 NO_NETWORK=1 PYTHONPATH=src:external/inspect_ai uv run pytest -q tests/inspect_agents`.

## Coding Style & Naming Conventions
- Python 3.11+, 4‑space indent, type hints required for public APIS.
- Naming: modules/files `snake_case.py`; functions `snake_case`; classes `PascalCase`.
- Keep imports light at module top; prefer local imports when heavy/optional (pattern used across repo).
- Docstrings: short, imperative, first line ≤ 80 chars.

## Testing Guidelines
- Framework: `pytest` (tests live under `tests/inspect_agents/`, named `test_*.py`).
- Default offline: set `NO_NETWORK=1`; keep tests deterministic and fast.
- Add tests for new behavior and regressions; cover env‑flag branches (e.g., `INSPECT_ENABLE_*`, FS modes).
- Example: `CI=1 NO_NETWORK=1 uv run pytest -q -k migration`.

## Commit & Pull Request Guidelines
- Conventional Commits: `type(scope): summary` (e.g., `fix(migration): execute side‑effect tools`).
- Keep commits atomic and logically independent; include rationale in body when useful.
- PRs: concise description, linked issues, reproduction (if bug), test updates, and example CLI output or logs when relevant.

## Security & Configuration Tips
- Never commit secrets; load from `.env` or `env_templates/inspect.env` (override with `INSPECT_ENV_FILE`).
- Filesystem mode: `INSPECT_AGENTS_FS_MODE=store|sandbox` (prefer `sandbox` for host FS edits).
- Tracing: set `INSPECT_TRACE_FILE` and `INSPECT_LOG_DIR` to capture artifacts for reviews.


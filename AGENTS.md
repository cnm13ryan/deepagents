# Repository Guidelines

This file governs engineering norms for this repository only. If your editor or machine also injects a global `~/.codex/AGENTS.md`, this repo‑local file takes precedence within the repo. Do not stack rules from the global file here.

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
- Test fast (default offline):
  - `CI=1 NO_NETWORK=1 PYTHONPATH=src:external/inspect_ai uv run pytest -q tests/inspect_agents`
  - Subset: append `-k <expr>` (e.g., `-k sandbox` or `-k truncation`).

## Programmatic Checks (Repo)
Run these checks automatically when contributing changes:
- Tests (primary):
  - Detect Python project via `pyproject.toml`; run
    `CI=1 NO_NETWORK=1 PYTHONPATH=src:external/inspect_ai uv run pytest -q tests/inspect_agents`.
  - Prefer deterministic subsets during iteration (e.g., `-k migration`, `-k limits`).
- Lint (optional): if `ruff` is configured, run `uv run ruff check`.
- Docs links (optional): build MkDocs locally if needed: `uv run mkdocs serve`.

Default step for bots/automation: if tests are discoverable, run the test command above before proposing changes.

## Coding Style & Naming Conventions
- Python 3.11+, 4‑space indent, type hints required for public APIS.
- Naming: modules/files `snake_case.py`; functions `snake_case`; classes `PascalCase`.
- Keep imports light at module top; prefer local imports when heavy/optional (pattern used across repo).
- Docstrings: short, imperative, first line ≤ 80 chars.

## Safety & Approvals
- Prefer safe defaults locally: use approval presets when enabling risky tools.
  - Python API: `from inspect_agents.approval import approval_preset, activate_approval_policies; activate_approval_policies(approval_preset("dev"))`.
  - CLI/evals: pass approval policies via your runner as documented in `docs/how-to/approvals.md`.
- Handoff exclusivity: when a handoff tool (`transfer_to_*`) is emitted alongside other tools in one assistant turn, only the handoff should proceed. The policy helper `handoff_exclusive_policy()` is available; presets may include it in future.

## Testing Guidelines
- Framework: `pytest` (tests live under `tests/inspect_agents/`, named `test_*.py`).
- Default offline: set `NO_NETWORK=1`; keep tests deterministic and fast.
- Add tests for new behavior and regressions; cover env‑flag branches (e.g., `INSPECT_ENABLE_*`, FS modes).
- Example: `CI=1 NO_NETWORK=1 uv run pytest -q -k migration`.

### Limits & Truncation tests
- Prefer deterministic limits (message/tool‑call) for assertions.
- Tool‑output truncation defaults to a 16 KiB envelope in upstream Inspect; repo tests may assert envelope behavior when an explicit limit is set.

## Commit & Pull Request Guidelines
- Conventional Commits: `type(scope): summary` (e.g., `fix(migration): execute side‑effect tools`).
- Keep commits atomic and logically independent; include rationale in body when useful.
- PRs: concise description, linked issues, reproduction (if bug), test updates, and example CLI output or logs when relevant.

## Security & Configuration Tips
- Never commit secrets; load from `.env` or `env_templates/inspect.env` (override with `INSPECT_ENV_FILE`).
- Filesystem mode: `INSPECT_AGENTS_FS_MODE=store|sandbox`.
  - Store (default): in‑memory virtual FS; safe for CI.
  - Sandbox: routes file ops to Inspect’s `text_editor`/`bash_session` against a host‑mounted sandbox.
  - Delete is intentionally disabled in sandbox mode by design; use store mode for delete operations.
- Sandbox guardrails implemented in code:
  - Root confinement under `INSPECT_AGENTS_FS_ROOT` (absolute; default `/repo`).
  - Symlink denial on read/write/edit.
  - Byte ceilings via `INSPECT_AGENTS_FS_MAX_BYTES` (read/write/edit).
- Tracing: set `INSPECT_TRACE_FILE` and `INSPECT_LOG_DIR` to capture artifacts for reviews.

## Tool Toggles (env)
- `INSPECT_ENABLE_THINK=1` — enable `think()` (default on when unset).
- `INSPECT_ENABLE_WEB_SEARCH=1` + provider creds (Tavily or Google CSE) — enable `web_search()`.
- `INSPECT_ENABLE_EXEC=1` — enable `bash()` and `python()` (use with approvals + sandbox).
- `INSPECT_ENABLE_WEB_BROWSER=1` — enable browser tools (heavy; sandbox recommended).
- `INSPECT_ENABLE_TEXT_EDITOR_TOOL=1` — optionally expose `text_editor()` directly.

## Model Selection
- Prefer `inspect_agents.model.resolve_model(...)` to build model strings from env:
  - Local default provider is `ollama` (override via `DEEPAGENTS_MODEL_PROVIDER`).
  - Role mapping via `INSPECT_ROLE_<ROLE>_MODEL` (+ optional `..._PROVIDER`) is supported; falls back to `inspect/<role>` when unmapped.

## Logs & Artifacts
- Transcript writer: `inspect_agents.logging.write_transcript()` appends JSONL events to `.inspect/logs/events.jsonl` (path override via `INSPECT_LOG_DIR`). See `docs/how-to/operations_logging_tracing.md`.

## Helpful Docs (in‑repo)
- Getting started: `docs/getting-started/inspect_agents_quickstart.md`
- Approvals: `docs/how-to/approvals.md`
- Filesystem & sandbox: `docs/how-to/filesystem.md`
- Tools reference: `docs/tools/README.md`
- Environment: `docs/reference/environment.md`
- Architecture & ADRs: `docs/ARCHITECTURE.md`, `docs/adr/README.md`

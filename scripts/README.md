# Scripts — Usage and Expected Behavior

This folder contains small utilities to help work with Inspect‑AI logs, docs, and local demos. All scripts are intended to run from the repo root unless otherwise noted.

## Prerequisites
- Python: 3.11+
- Environment: `uv` recommended (`uv sync`), or an environment where `inspect-ai` is installed (see `pyproject.toml`).
- CLI: prefer `uv run` for Python/Inspect commands; falls back to `inspect` if available on PATH.
- Optional tools: `jq` for JSON filtering in examples.

---

## `export_eval_json.sh`
- Purpose: Export a single Inspect log (either `.eval` or `.json` on disk or a URI like `file://` or `s3://`) to JSON.
- Behavior: Writes `eval.json` by default into the same directory as the script (this folder), overwriting if present. Supports a custom output path and auto-naming.
- Usage:
  ```bash
  # Default output to scripts/eval.json
  scripts/export_eval_json.sh .inspect/logs/2025-09-04T14-05-28+01-00_iterative-task_QSZc4iMNgTB3jE2ny2dxQq.eval

  # Custom output path
  scripts/export_eval_json.sh --out /tmp/eval.json .inspect/logs/2025-09-04T14-05-28+01-00_iterative-task_QSZc4iMNgTB3jE2ny2dxQq.eval
  # or
  scripts/export_eval_json.sh -o .inspect/logs/eval.json .inspect/logs/2025-09-04T14-05-28+01-00_iterative-task_QSZc4iMNgTB3jE2ny2dxQq.eval

  # Auto-name output as <basename>.json next to the input file (local paths or file://)
  scripts/export_eval_json.sh --auto-name .inspect/logs/2025-09-04T14-05-28+01-00_iterative-task_QSZc4iMNgTB3jE2ny2dxQq.eval
  ```
- Notes:
  - Prefers `uv run inspect log dump`; falls back to `inspect log dump` if `uv` is not found.
  - Accepts local paths or URIs; for local paths it checks file existence.
  - Creates parent directories for `--out` if they don’t exist.
  - `--auto-name` places `<input-basename>.json` next to the input file when the input is a local path or `file://` URI; for remote URIs (e.g., `s3://`) it falls back to the script directory.
  - Exit codes: non‑zero on missing args, missing file (local paths), or CLI failure.

---

## `read_log_eval.py`
- Purpose: Inspect and materialize data frames from the latest (or specified) `.eval` log.
- Behavior:
  - Loads env from `.env` and `env_templates/inspect.env` (without overriding real env vars).
  - Resolves log dir from `INSPECT_LOG_DIR` (default `.inspect/logs`).
  - If no file is provided, picks the newest `*.eval`.
  - Prints small previews and writes CSV snapshots to the current working directory:
    - `eval_overview.csv`, `sample_data.csv`, `message_data.csv`, `event_data.csv`.
- Usage:
  ```bash
  # Analyze newest eval
  uv run python scripts/read_log_eval.py
  
  # List recent logs
  uv run python scripts/read_log_eval.py --list
  
  # Analyze a specific file (relative to INSPECT_LOG_DIR or absolute)
  uv run python scripts/read_log_eval.py --file 2025-09-04T14-05-28+01-00_iterative-task.eval
  ```
- Notes:
  - Requires `inspect-ai` (declared in `pyproject.toml`).
  - If you installed the repo in editable mode, no `PYTHONPATH` tweaks are needed.

---

## `manual_approval_check.py`
- Purpose: Manual, offline sanity checks for approval presets, sensitive tool patterns, and redaction.
- Behavior:
  - Mocks `inspect_ai.*` modules as needed (no network, no external deps).
  - Imports `src.inspect_agents.approval` and runs a few checks:
    - Sensitive tool detection matches expected names.
    - `dev` preset escalates sensitive tools.
    - `prod` preset terminates and redacts sensitive args.
    - `redact_arguments` masks sensitive keys.
- Usage:
  ```bash
  CI=1 NO_NETWORK=1 PYTHONPATH=src uv run python scripts/manual_approval_check.py
  ```
- Output: Human‑readable lines with ✓/✗ markers and decisions (`approve|escalate|terminate`).

---

## `quickstart_toy.py`
- Purpose: Minimal agent demo that returns `DONE` via a `submit` tool call.
- Behavior: Runs an agent supervisor with a tiny model shim and prints the completion.
- Usage:
  ```bash
  uv run python scripts/quickstart_toy.py
  # Expected: "Completion: DONE"
  ```

---

## `sweep_status.py`
- Purpose: Docs maintenance helper to keep status markers consistent across docs.
- Behavior:
  - Scans selected files under `docs/` and computes minimal, deterministic rewrites.
  - Default mode prints a unified diff (non‑destructive). Use `--write` to apply.
- Usage:
  ```bash
  # Check only (prints diffs if any)
  uv run python scripts/sweep_status.py
  
  # Apply changes in place
  uv run python scripts/sweep_status.py --write
  ```
- Notes: stdlib‑only; runs offline.

---

## Tips
- Use `INSPECT_LOG_DIR` to point to your log root when working with logs (defaults vary by tooling).
- For very large logs, prefer header-only previews with the CLI: `uv run inspect log dump <path> --header-only | jq .`.

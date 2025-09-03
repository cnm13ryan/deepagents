"""
Analyze the most recent Inspect-AI eval log.

Behavior
- Loads environment from .env (and optional INSPECT_ENV_FILE) without overriding real env vars.
- Resolves log directory from INSPECT_LOG_DIR (defaults to .inspect/logs).
- Finds the latest "*.eval" file and inspects it using inspect_ai.analysis tools.
- Prints small previews and writes CSV snapshots to the current directory.

Usage
  uv run python scripts/read_log_eval.py            # analyze latest
  uv run python scripts/read_log_eval.py --list     # list recent logs
  uv run python scripts/read_log_eval.py --file <path/to/log.eval>
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from inspect_ai.analysis import evals_df, events_df, messages_df, samples_df

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_env_files() -> None:
    """Load .env files in a reasonable precedence without overriding real env.

    Precedence among files (highest to lowest):
      - INSPECT_ENV_FILE (if set)
      - repo-root .env
      - env_templates/inspect.env (fill-ins)
    """
    try:
        from dotenv import load_dotenv  # type: ignore

        explicit = os.getenv("INSPECT_ENV_FILE")
        if explicit:
            load_dotenv(explicit, override=False)

        load_dotenv(REPO_ROOT / ".env", override=False)
        load_dotenv(REPO_ROOT / "env_templates" / "inspect.env", override=False)
        return
    except Exception:
        # Fall back to a tiny parser; best-effort only.
        pass

    def _load_one(path: Path) -> None:
        if not path.exists():
            return
        try:
            for raw in path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
        except Exception:
            return

    _load_one(REPO_ROOT / ".env")
    _load_one(REPO_ROOT / "env_templates" / "inspect.env")


def _resolve_log_dir() -> Path:
    raw = os.getenv("INSPECT_LOG_DIR", ".inspect/logs").strip()
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path


def _list_eval_logs(dirpath: Path, limit: int = 20) -> list[Path]:
    candidates = [p for p in dirpath.glob("*.eval") if p.is_file() and not p.name.endswith("~")]
    # Sort by mtime desc
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[:limit]


def _pick_latest_eval(dirpath: Path) -> Path | None:
    logs = _list_eval_logs(dirpath, limit=1)
    return logs[0] if logs else None


def _analyze(log_file: Path) -> None:
    print(f"Analyzing eval log: {log_file}")
    eval_data = evals_df(str(log_file))
    sample_data = samples_df(str(log_file))
    message_data = messages_df(str(log_file))
    event_data = events_df(str(log_file))

    # Console summaries
    print("\nEvaluation Overview (head):")
    print(eval_data.head())
    print("\nSample Data (head):")
    print(sample_data.head())
    print("\nMessage Data (head):")
    print(message_data.head())
    print("\nEvent Data (head):")
    print(event_data.head())

    # Persist CSVs for offline inspection
    eval_data.to_csv("eval_overview.csv", index=False)
    sample_data.to_csv("sample_data.csv", index=False)
    message_data.to_csv("message_data.csv", index=False)
    event_data.to_csv("event_data.csv", index=False)
    print("\nWrote: eval_overview.csv, sample_data.csv, message_data.csv, event_data.csv")


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect the latest Inspect-AI eval log.")
    parser.add_argument("--file", type=str, help="Explicit path to a .eval log file")
    parser.add_argument("--list", action="store_true", help="List recent logs and exit")
    args = parser.parse_args()

    _load_env_files()
    log_dir = _resolve_log_dir()
    if not log_dir.exists():
        raise SystemExit(f"Log directory not found: {log_dir}")

    if args.list:
        logs = _list_eval_logs(log_dir, limit=50)
        if not logs:
            print(f"No .eval logs found in {log_dir}")
            return 0
        print(f"Recent eval logs in {log_dir} (newest first):")
        for p in logs:
            print(f"  {p.name}")
        return 0

    log_file: Path | None = None
    if args.file:
        log_file = Path(args.file).expanduser()
        if not log_file.is_absolute():
            log_file = (log_dir / log_file).resolve()
        if not (log_file.exists() and log_file.suffix == ".eval"):
            raise SystemExit(f"Provided file is not a valid .eval: {log_file}")
    else:
        log_file = _pick_latest_eval(log_dir)
        if not log_file:
            raise SystemExit(f"No .eval logs found in {log_dir}")

    _analyze(log_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

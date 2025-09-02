from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


DEFAULT_LOG_DIR = ".inspect/logs"
REDACT_KEYS = {"api_key", "authorization", "file_text", "content"}


def _ensure_dir(path: str) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _redact(obj: Any, key: str | None = None) -> Any:
    if isinstance(obj, dict):
        return {k: _redact(v, k) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact(v, key) for v in obj]
    if key in REDACT_KEYS:
        try:
            if isinstance(obj, str) and obj:
                return "[REDACTED]"
        except Exception:
            return "[REDACTED]"
    return obj


def _event_to_dict(ev: Any) -> dict[str, Any]:
    data: dict[str, Any] = {}
    # shallow attribute dump
    for k, v in vars(ev).items():
        data[k] = _redact(v, k)
    data["type"] = ev.__class__.__name__
    return data


def write_transcript(log_dir: str | None = None) -> str:
    """Write current Inspect transcript events to a JSONL log file.

    Returns the log file path. Redacts sensitive fields by default.
    """
    from inspect_ai.log._transcript import transcript

    log_dir = log_dir or os.getenv("INSPECT_LOG_DIR", DEFAULT_LOG_DIR)
    _ensure_dir(log_dir)
    file_path = str(Path(log_dir) / "events.jsonl")

    with open(file_path, "a", encoding="utf-8") as fp:
        for ev in transcript().events:
            try:
                fp.write(json.dumps(_event_to_dict(ev), ensure_ascii=False) + "\n")
            except Exception:
                # best-effort: write a minimal record
                fp.write(json.dumps({"type": ev.__class__.__name__}) + "\n")

    return file_path


__all__ = ["write_transcript", "DEFAULT_LOG_DIR"]


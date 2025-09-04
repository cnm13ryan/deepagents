# feat(observability): extract tool-event logging and one-time limit log

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

# Local defaults (env-configurable)
_OBS_TRUNCATE = int(os.getenv("INSPECT_TOOL_OBS_TRUNCATE", "200"))


def _parse_int(env_val: str | None) -> int | None:
    try:
        if env_val is None:
            return None
        val = int(env_val.strip())
        if val < 0:
            return None
        return val
    except Exception:
        return None


def maybe_emit_effective_tool_output_limit_log() -> None:
    """Emit a single structured log with the effective tool-output limit.

    Semantics preserved from tools._maybe_emit_effective_tool_output_limit_log:
    - Reads optional env override `INSPECT_MAX_TOOL_OUTPUT` (bytes).
    - If set and upstream GenerateConfig has no explicit limit, set it once
      to keep precedence: explicit arg > GenerateConfig > env > fallback 16 KiB.
    - Logs a one-time `tool_event` with fields:
        { tool: "observability", phase: "info",
          effective_tool_output_limit: <int>, source: "env"|"default" }
    - One-time behavior is coordinated via `inspect_agents.tools._EFFECTIVE_LIMIT_LOGGED`
      when available to preserve test reset hooks; otherwise, a local fallback is used.
    """
    # Coordinate one-time behavior through tools module if available
    tmod = None
    try:
        import inspect_agents.tools as _tmod  # type: ignore

        tmod = _tmod
        if getattr(tmod, "_EFFECTIVE_LIMIT_LOGGED", False):
            return
    except Exception:
        # Local fallback flag when tools module isn't imported yet
        if getattr(maybe_emit_effective_tool_output_limit_log, "_logged", False):  # type: ignore[attr-defined]
            return

    env_raw = os.getenv("INSPECT_MAX_TOOL_OUTPUT")
    env_limit = _parse_int(env_raw)

    source = "default"
    effective = 16 * 1024
    try:
        from inspect_ai.model._generate_config import (  # type: ignore
            active_generate_config,
            set_active_generate_config,
        )

        cfg = active_generate_config()
        # If env is provided and config has no explicit limit, adopt env
        if env_limit is not None and getattr(cfg, "max_tool_output", None) is None:
            try:
                new_cfg = cfg.merge({"max_tool_output": env_limit})  # type: ignore[arg-type]
                set_active_generate_config(new_cfg)
            except Exception:
                try:
                    cfg.max_tool_output = env_limit  # type: ignore[attr-defined]
                except Exception:
                    pass

        # Resolve effective limit
        cfg_limit = getattr(active_generate_config(), "max_tool_output", None)
        if cfg_limit is not None:
            effective = int(cfg_limit)
        elif env_limit is not None:
            effective = env_limit
        source = "env" if env_limit is not None else "default"
    except Exception:
        if env_limit is not None:
            effective = env_limit
            source = "env"

    # Use the historical logger name for compatibility
    logger = logging.getLogger("inspect_agents.tools")
    try:
        payload = {
            "tool": "observability",
            "phase": "info",
            "effective_tool_output_limit": effective,
            "source": source,
        }
        logger.info("tool_event %s", json.dumps(payload, ensure_ascii=False))
    except Exception:
        logger.info(
            "tool_event %s",
            {"tool": "observability", "phase": "info", "effective_tool_output_limit": effective, "source": source},
        )

    # Mark as logged
    if tmod is not None:
        try:
            setattr(tmod, "_EFFECTIVE_LIMIT_LOGGED", True)
        except Exception:
            pass
    else:
        setattr(maybe_emit_effective_tool_output_limit_log, "_logged", True)  # type: ignore[attr-defined]


def _redact_and_truncate(payload: dict[str, Any] | None, max_len: int | None = None) -> dict[str, Any]:
    """Redact sensitive keys and truncate large string fields.

    - Redaction uses approval.redact_arguments to apply the shared REDACT_KEYS policy.
    - Truncation applies to string values > max_len chars (default from env).
    """
    if not payload:
        return {}
    try:
        from .approval import redact_arguments
    except Exception:
        redacted = dict(payload)
    else:
        redacted = redact_arguments(dict(payload))  # type: ignore[arg-type]

    limit = max_len if (max_len is not None and max_len > 0) else _OBS_TRUNCATE

    def _truncate(v: Any) -> Any:
        try:
            if isinstance(v, str) and limit and len(v) > limit:
                return v[:limit] + f"...[+{len(v) - limit} chars]"
            return v
        except Exception:
            return "[UNSERIALIZABLE]"

    return {k: _truncate(v) for k, v in redacted.items()}


def log_tool_event(
    name: str,
    phase: str,
    args: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
    t0: float | None = None,
) -> float:
    """Emit a minimal structured log line for tool lifecycle.

    Returns a perf counter when phase == "start" so callers can pass it back
    on "end"/"error" to compute a duration.
    """
    # Emit one-time effective limit log on the very first tool event
    maybe_emit_effective_tool_output_limit_log()

    logger = logging.getLogger("inspect_agents.tools")  # preserve logger name
    now = time.perf_counter()
    data: dict[str, Any] = {
        "tool": name,
        "phase": phase,
    }
    if args:
        # Normalization policy: rewrite raw content fields to length metadata first
        try:
            norm = dict(args)
            mapping: list[tuple[str, str]] = [
                ("content", "content_len"),
                ("file_text", "file_text_len"),
                ("old_string", "old_len"),
                ("new_string", "new_len"),
            ]
            for src, dst in mapping:
                if src in norm and isinstance(norm[src], str):
                    try:
                        norm[dst] = len(norm[src])
                    except Exception:
                        norm[dst] = "[len_error]"
                    norm.pop(src, None)
        except Exception:
            norm = args
        data["args"] = _redact_and_truncate(norm)
    if t0 is not None and phase in ("end", "error"):
        try:
            data["duration_ms"] = round((now - t0) * 1000, 2)
        except Exception:
            pass
    if extra:
        for k, v in extra.items():
            if k not in data:
                data[k] = v

    try:
        logger.info("tool_event %s", json.dumps(data, ensure_ascii=False))
    except Exception:
        logger.info("tool_event %s", {k: ("[obj]" if k == "args" else v) for k, v in data.items()})

    return now if phase == "start" else (t0 or now)


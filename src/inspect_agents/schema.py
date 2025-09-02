from __future__ import annotations

import re
from typing import Literal

ErrorCode = Literal[
    "MISSING_REQUIRED",
    "TYPE_MISMATCH",
    "EXTRA_FIELD",
    "PARSING_ERROR",
    "UNKNOWN_SCHEMA_ERROR",
]


_PATTERNS: list[tuple[ErrorCode, re.Pattern[str]]] = [
    ("MISSING_REQUIRED", re.compile(r"required property|Required parameter .* not provided", re.I)),
    ("TYPE_MISMATCH", re.compile(r"not of type|Unable to convert", re.I)),
    ("EXTRA_FIELD", re.compile(r"Additional properties are not allowed", re.I)),
]


def classify_tool_arg_error(message: str | None) -> ErrorCode:
    """Classify a tool-argument error message into a stable error code.

    Accepts messages from either JSON Schema (Draft7) validation or Inspect's
    tool_param coercion and returns a coarse-grained, stable code suitable for
    testing and operator UX.
    """
    if not message:
        return "UNKNOWN_SCHEMA_ERROR"
    for code, pat in _PATTERNS:
        if pat.search(message):
            return code
    # Distinguish general parsing failures
    if "Error parsing" in message:
        return "PARSING_ERROR"
    return "UNKNOWN_SCHEMA_ERROR"


__all__ = ["classify_tool_arg_error", "ErrorCode"]


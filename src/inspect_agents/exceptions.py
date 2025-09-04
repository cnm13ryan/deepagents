# feat(exceptions): add ToolException shim for tools/fs imports

"""Centralized exception types for inspect_agents.

Provides `ToolException` by re-exporting the implementation from the
vendored Inspect Tool Support package when available. If the vendor package
is not importable (e.g., in very minimal unit-test stubs), falls back to a
lightweight local definition so that importing `inspect_agents.tools` and
`inspect_agents.tools_files` remains reliable.
"""

from __future__ import annotations

try:  # Prefer the canonical implementation from Inspect Tool Support
    from inspect_tool_support._util.common_types import (  # type: ignore
        ToolException as _ToolException,
    )
except Exception:  # Fallback to a simple local definition for test stubs
    class _ToolException(Exception):  # type: ignore[no-redef]
        """Raised when a tool encounters an error."""

        def __init__(self, message: str):
            self.message = message


# Public export
ToolException = _ToolException

__all__ = ["ToolException"]


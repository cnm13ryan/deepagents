from __future__ import annotations

"""Shared exception aliases for inspect_agents.

Provides a single import location for ToolException that resolves to the
upstream inspect_tool_support exception when available, with a minimal
fallback for environments where the package is not installed.
"""

# Prefer the upstream ToolException when present (ensures consistent typing
# and error propagation across tools). Fall back to a local shim that preserves
# the message attribute shape used in tests.
try:  # pragma: no cover - exercised via integration when upstream is present
    from inspect_tool_support._util.common_types import (  # type: ignore
        ToolException as ToolException,  # noqa: N811 - keep public name
    )
except Exception:  # pragma: no cover - simple shim
    class ToolException(Exception):  # type: ignore[no-redef]  # noqa: N818
        def __init__(self, message: str):
            self.message = message
            super().__init__(message)


"""Lightweight package exports.

Avoid importing submodules that transitively require optional, heavy
dependencies (e.g., langgraph) during top-level package import so that
consumers can import `deepagents.model` without a full runtime.
# refactor(package): avoid heavyweight imports at package import time
"""

from deepagents.model import get_default_model

__all__ = [
    "get_default_model",
]

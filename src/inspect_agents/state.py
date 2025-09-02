"""Core state models for the Inspect‑AI rewrite.

This module provides Store-backed, JSON-serializable state models:
- `Todo` (Pydantic BaseModel)
- `Todos` (StoreModel with `todos: list[Todo]`)
- `Files` (StoreModel with `files: dict[str, str]`)

Notes
- Keys are automatically namespaced by `StoreModel` as
  `ClassName[:instance]:field`. Do not add custom key fields.
- Isolation: prefer `Files(instance=<agent_name>)` to isolate per-agent
  file state; keep `Todos` shared by default.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field
from inspect_ai.util._store_model import StoreModel


class Todo(BaseModel):
    """Todo to track (JSON-serializable)."""

    content: str
    status: Literal["pending", "in_progress", "completed"]


class Todos(StoreModel):
    """Todos stored in Inspect-AI's Store.

    Namespaced key: `Todos[:instance]:todos`
    """

    todos: list[Todo] = Field(default_factory=list)

    # Convenience accessors
    def get_todos(self) -> list[Todo]:
        return self.todos

    def set_todos(self, todos: list[Todo]) -> None:
        self.todos = todos


class Files(StoreModel):
    """Text file store backed by Inspect-AI's Store.

    Namespaced key: `Files[:instance]:files`
    """

    files: dict[str, str] = Field(default_factory=dict)

    def list_files(self) -> list[str]:
        return list(self.files.keys())

    def get_file(self, path: str) -> str | None:
        return self.files.get(path)

    def put_file(self, path: str, content: str) -> None:
        # Replace with a copied mapping to ensure store update semantics
        new_files = dict(self.files)
        new_files[path] = content
        self.files = new_files

    def delete_file(self, path: str) -> None:
        """Delete a file entry if it exists.

        Uses a copied mapping update to ensure the StoreModel writes
        a new value into the Store (so changes are captured/transcripted).
        """
        if path in self.files:
            new_files = dict(self.files)
            new_files.pop(path, None)
            self.files = new_files

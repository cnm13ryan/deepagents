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

import logging
from typing import Literal

from inspect_ai.util._store_model import StoreModel
from inspect_ai.log._transcript import track_store_changes
from pydantic import BaseModel, Field


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
        # Emit a StoreEvent for this mutation
        with track_store_changes():
            self.todos = todos

    def update_status(
        self,
        index: int,
        status: Literal["pending", "in_progress", "completed"],
        allow_direct_complete: bool = False,
    ) -> str | None:
        """Update a single todo's status with validated transitions.

        Allowed transitions:
        - pending -> in_progress
        - in_progress -> completed
        - pending -> completed (only when allow_direct_complete is True)

        Args:
            index: Zero-based index into the todos list.
            status: New status value.
            allow_direct_complete: Permit pending -> completed with a warning.

        Returns:
            Optional warning string when a direct completion is allowed.

        Raises:
            IndexError: If index is out of range.
            ValueError: If status is invalid or transition is not allowed.
        """
        if index < 0 or index >= len(self.todos):
            raise IndexError(f"Invalid todo index {index}; list has {len(self.todos)} items")

        if status not in ("pending", "in_progress", "completed"):
            raise ValueError(f"Invalid status '{status}'")

        current = self.todos[index].status
        if current == status:
            # No-op transition
            return None

        warning: str | None = None
        if current == "pending" and status == "in_progress":
            pass  # allowed
        elif current == "in_progress" and status == "completed":
            pass  # allowed
        elif current == "pending" and status == "completed":
            if not allow_direct_complete:
                raise ValueError("Invalid transition pending -> completed (set allow_direct_complete=True to permit)")
            warning = "Direct transition pending->completed allowed (allow_direct_complete=True)"
            try:
                logging.getLogger(__name__).warning(warning)
            except Exception:
                pass
        else:
            # Disallow other transitions (e.g., completed -> in_progress)
            raise ValueError(f"Invalid status transition: {current} -> {status}")

        # Apply update by copying the Todo (pydantic model copy)
        try:
            updated = self.todos[index].model_copy(update={"status": status})
        except Exception:
            # Fallback for older pydantic versions if needed
            updated = Todo(content=self.todos[index].content, status=status)

        new_list = list(self.todos)
        new_list[index] = updated
        # Emit a StoreEvent for this mutation
        with track_store_changes():
            self.todos = new_list

        return warning


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
        # Emit a StoreEvent for this mutation
        with track_store_changes():
            self.files = new_files

    def delete_file(self, path: str) -> None:
        """Delete a file entry if it exists.

        Uses a copied mapping update to ensure the StoreModel writes
        a new value into the Store (so changes are captured/transcripted).
        """
        if path in self.files:
            new_files = dict(self.files)
            new_files.pop(path, None)
            # Emit a StoreEvent for this mutation
            with track_store_changes():
                self.files = new_files

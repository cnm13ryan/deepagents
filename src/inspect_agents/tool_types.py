"""Pydantic input models for inspect_agents tools with extra="forbid".

This module provides Pydantic models for validating tool inputs with strict
field validation, detecting unknown fields and typos early.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FilesToolParams(BaseModel):
    """Pydantic model for unified files tool parameters with strict validation."""

    model_config = ConfigDict(extra="forbid")

    command: Literal["ls", "read", "write", "edit", "delete"] = Field(description="File operation command")
    file_path: str | None = Field(None, description="Path to file (required for read, write, edit, delete)")
    content: str | None = Field(None, description="File content (required for write)")
    offset: int = Field(0, description="Line offset for read (0-based)")
    limit: int = Field(2000, description="Max lines to return for read")
    old_string: str | None = Field(None, description="String to replace (required for edit)")
    new_string: str | None = Field(None, description="Replacement string (required for edit)")
    replace_all: bool = Field(False, description="Replace all occurrences for edit")
    instance: str | None = Field(None, description="Optional Files instance for isolation")


class TodoItem(BaseModel):
    """Single todo item model."""

    model_config = ConfigDict(extra="forbid")

    content: str = Field(description="Todo item content")
    status: Literal["pending", "in_progress", "completed"] = Field(default="pending", description="Todo status")


class WriteTodosParams(BaseModel):
    """Parameters for write_todos tool."""

    model_config = ConfigDict(extra="forbid")

    todos: list[TodoItem] = Field(description="List of todo items to write")


class UpdateTodoStatusParams(BaseModel):
    """Parameters for update_todo_status tool."""

    model_config = ConfigDict(extra="forbid")

    todo_index: int = Field(description="Index of todo to update (0-based)")
    status: Literal["pending", "in_progress", "completed"] = Field(description="New status for todo")
    allow_direct_complete: bool = Field(default=False, description="Allow pending->completed transition directly")

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, ValidationError

from .agents import build_subagents, build_supervisor
from .approval import approval_from_interrupt_config


class SupervisorCfg(BaseModel):
    prompt: str
    attempts: int | None = None
    truncation: Literal["auto", "disabled"] | None = None
    model: Any | None = None


class SubAgentCfg(BaseModel):
    name: str
    description: str
    prompt: str
    tools: list[str] | None = None
    model: Any | None = None
    mode: Literal["handoff", "tool"] | None = None
    # Experimental quarantine controls (prefer explicit input_filter when set)
    context_scope: Literal["strict", "scoped"] | None = None
    include_state_summary: bool | None = None


class RootConfig(BaseModel):
    supervisor: SupervisorCfg
    subagents: list[SubAgentCfg] | None = Field(default=None)
    approvals: dict[str, Any] | None = Field(default=None)
    limits: list[Any] | None = Field(default=None)


def load_yaml(source: str | Path | dict[str, Any]) -> RootConfig:
    data: dict[str, Any]
    if isinstance(source, dict):
        data = source
    else:
        text = Path(source).read_text(encoding="utf-8") if Path(str(source)).exists() else str(source)
        data = yaml.safe_load(text) or {}
    try:
        return RootConfig(**data)
    except ValidationError as e:
        # Provide a concise message for tests/users
        raise ValueError(f"Invalid config: {e}")


def build_from_config(cfg: RootConfig, *, model: Any | None = None) -> tuple[object, list[object], list[Any]]:
    """Build a supervisor agent, tools, and approval policies from parsed config.

    Returns (agent, tools, approvals)
    """
    sub_tools: list[object] = []
    if cfg.subagents:
        # Build sub-agent tools using base tools (write_todos/fs) as universe
        from .tools import edit_file, ls, read_file, write_file, write_todos

        base_universe = [write_todos(), write_file(), read_file(), ls(), edit_file()]

        # Convert pydantic models to dicts expected by build_subagents
        sub_cfgs = [sa.model_dump(exclude_none=True) for sa in cfg.subagents]

        # Map experimental context_scope/include_state_summary to input_filter when provided
        # (explicit input_filter in config would still override)
        try:
            from inspect_agents.filters import (
                scoped_quarantine_filter,
                strict_quarantine_filter,
            )
        except Exception:
            strict_quarantine_filter = scoped_quarantine_filter = None  # type: ignore

        for sc in sub_cfgs:
            if "input_filter" in sc:
                continue  # explicit wins
            scope = sc.pop("context_scope", None)
            include_summary = sc.pop("include_state_summary", None)
            if scope == "strict" and callable(strict_quarantine_filter):
                sc["input_filter"] = strict_quarantine_filter()
            elif scope == "scoped" and callable(scoped_quarantine_filter):
                sc["input_filter"] = scoped_quarantine_filter(
                    include_state_summary=True if include_summary is None else bool(include_summary)
                )

        # Ensure each sub-agent has a model (fallback to a tiny echo agent)
        from inspect_ai.agent._agent import agent as as_agent

        @as_agent
        def _default_sub():
            async def execute(state, tools):
                from inspect_ai.model._chat_message import ChatMessageAssistant

                state.messages.append(ChatMessageAssistant(content="[subagent]"))
                return state

            return execute

        for sc in sub_cfgs:
            sc.setdefault("model", _default_sub())

        sub_tools = build_subagents(
            configs=sub_cfgs,
            base_tools=base_universe,
        )

    # Resolve approvals
    approvals_cfg = cfg.approvals or {}
    approvals = approval_from_interrupt_config(approvals_cfg)

    # Build supervisor
    sup = cfg.supervisor
    agent = build_supervisor(
        prompt=sup.prompt,
        tools=sub_tools,
        attempts=sup.attempts or 1,
        model=model or sup.model,
        truncation=sup.truncation or "disabled",
    )

    # Aggregate active tools (subtools only; supervisor already includes built-ins)
    active_tools = sub_tools

    return agent, active_tools, approvals


def load_and_build(
    source: str | Path | dict[str, Any],
    *,
    model: Any | None = None,
) -> tuple[object, list[object], list[Any]]:
    return build_from_config(load_yaml(source), model=model)


__all__ = ["load_yaml", "build_from_config", "load_and_build", "RootConfig", "SupervisorCfg", "SubAgentCfg"]

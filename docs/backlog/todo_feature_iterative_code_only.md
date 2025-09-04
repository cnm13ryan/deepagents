# TODO: Iterative Agent — `code_only` Flag

## Context & Motivation
- Purpose: provide a mode that biases toward file operations and hides execute/search by default.
- Problem: some workflows prohibit exec/network; current defaults can append standard tools via env.
- Value: safer defaults for code‑only editing flows.

## Implementation Guidance
- Examine: `src/inspect_agents/iterative.py` (toolset and system message), `src/inspect_agents/tools.py` (`standard_tools()` stays env‑gated).
- Grep tokens: `_base_tools()`, `_default_system_message()`, `standard_tools(`.

## Scope Definition
- Implement: add `code_only: bool = False` to builder. When true, do not append `standard_tools()` and tweak system message to emphasize read/edit only and no exec/web.
- Tests: inspect built tool names via `ToolDef` to ensure presence/absence per flag.

## Success Criteria
- Behavior: toolset differs per flag; system message updated only when `code_only=True`.
- Tests: new unit tests pass.

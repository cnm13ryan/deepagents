# TODO: Iterative Agent — Unified Global Tool‑Output Cap (explicit param + early config)

Status: DONE (2025-09-04)
- Implemented in `build_iterative_agent` via `max_tool_output_bytes` and early `GenerateConfig` application; tool execution passes `max_output` when supported. See code: `src/inspect_agents/iterative.py` (param and early config) and tool observability: `src/inspect_agents/tools.py` (`_maybe_emit_effective_tool_output_limit_log`).
- Tests: integration/unit coverage exists around truncation envelope and limits; see tests under `tests/integration/inspect_agents/test_iterative_truncation_param.py` and related truncation tests.

## Context & Motivation
- Purpose: Apply a consistent maximum size to tool outputs (including standard `bash`/`python`) to prevent transcript bloat and memory spikes.
- Problem: Current cap relies on an env override (`INSPECT_MAX_TOOL_OUTPUT`) set lazily in the tools layer; tools invoked before that may not be capped.
- Value: Deterministic behavior across environments; safer defaults for long iterative runs.
- Constraints: Prefer non-invasive changes; set cap early at agent start. Respect precedence: explicit param > active GenerateConfig > env > fallback.

## Implementation Guidance
- Examine:
  - `src/inspect_agents/iterative.py` — agent initialization before the loop and model call sites.
  - `src/inspect_agents/tools.py` — one‑time env application and observability log (`_maybe_emit_effective_tool_output_limit_log`).
- Grep:
  - `GenerateConfig(timeout=`, `active_generate_config`, `set_active_generate_config`, `max_tool_output`, `execute_tools(`.
- Steps:
  1) Extend `build_iterative_agent` signature with `max_tool_output_bytes: int | None = None`.
  2) At agent construction (before the loop), set `active_generate_config().max_tool_output` when the param is provided or when env `INSPECT_MAX_TOOL_OUTPUT` is set and the active config lacks a value. Use merge semantics to avoid in-place mutation.
  3) When executing tools:
     - If an API allows `max_output` (feature-detect), pass the same cap explicitly; otherwise rely on the active config cap.
  4) Emit a one‑time log of the effective cap and its source (param/env/default) for observability.

## Scope Definition
- Iterative agent only; leave supervisor agent unchanged for now.
- No changes to Inspect internals; use public `active_generate_config` APIs.

## Success Criteria
- Behavior: With `max_tool_output_bytes=4096`, all tool outputs captured in transcripts are truncated to ≤4 KiB. Standard tools follow the cap when set early.
- Testing: Integration test that invokes a tool producing >10 KiB; assert truncation and a single observability log line of effective cap.
- Compatibility: Passing the param overrides env; env overrides default 16 KiB; absence of param/env keeps current behavior.

# TODO — Gate text_editor Exposure Behind Preflight (Optional)

## Context & Motivation
- Purpose: avoid exposing a `text_editor()` tool when it will likely fail due to missing sandbox, reducing confusion in misconfigured environments.
- Problem: `standard_tools()` currently exposes `text_editor()` based on env flags + fs mode, regardless of sandbox health.
- Impact: cleaner tool surface; fewer runtime errors; better UX.
- Constraints: `standard_tools()` is sync; avoid introducing async or heavy checks.

## Implementation Guidance
- Files to examine:
  - `src/inspect_agents/tools.py` — `standard_tools()` conditional that appends `text_editor()`. 〖F:src/inspect_agents/tools.py†L258-L261〗
  - `src/inspect_agents/tools_files.py` — preflight helper (async) for reference; recognize in-process stubs.
- Greppables: `INSPECT_ENABLE_TEXT_EDITOR_TOOL`, `_use_sandbox_fs`, `text_editor()`.
- Approach (best-effort):
  - Additionally require either presence of the in-process editor stub (`"inspect_ai.tool._tools._text_editor" in sys.modules`) or a strict env hint (`INSPECT_SANDBOX_PREFLIGHT=force`) before exposing the tool.
  - Document that final authoritative check happens inside the tool path; this gate reduces—but does not eliminate—runtime failures.

## Scope Definition
- Small change inside `standard_tools()`; keep default behavior unless env explicitly requests strict gating.
- Do not introduce async into `standard_tools()`.

## Success Criteria
- With missing sandbox and no stubs, and strict gating enabled, `text_editor()` is omitted.
- With stubs or real sandbox, tool is present (when enabled by env).
- No regressions to other tools exposure logic.


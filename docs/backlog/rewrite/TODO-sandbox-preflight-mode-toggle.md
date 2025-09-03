# TODO — Preflight Mode Toggle (INSPECT_SANDBOX_PREFLIGHT=auto|skip|force)

## Context & Motivation
- Purpose: give users control over sandbox preflight behavior: keep default auto-fallback, enforce strict “force” in prod, or “skip” checks in constrained/offline CI.
- Problem: preflight currently always attempts once and falls back. Some teams want failures to be loud (prod), others want zero sandbox attempts/warnings in CI.
- Impact: predictable behavior across environments; fewer surprising fallbacks; simpler CI noise profile; enables SRE policy enforcement.
- Constraints: retain zero/near-zero hot-path overhead; preserve unit-test stubbing (no Docker); avoid API surface changes.

## Implementation Guidance
- Files to examine:
  - `src/inspect_agents/tools_files.py` — preflight helper `_ensure_sandbox_ready`, cache vars `_SANDBOX_READY`, `_SANDBOX_WARN`, and sandbox call sites in `execute_ls/read/write/edit`. 〖F:src/inspect_agents/tools_files.py†L25-L89〗 〖F:src/inspect_agents/tools_files.py†L234-L241〗 〖F:src/inspect_agents/tools_files.py†L322-L329〗 〖F:src/inspect_agents/tools_files.py†L443-L450〗 〖F:src/inspect_agents/tools_files.py†L493-L500〗
  - `external/inspect_ai/src/inspect_ai/tool/_tool_support_helpers.py` — `tool_support_sandbox(...)` behavior and `PrerequisiteError` guidance text. 〖F:external/inspect_ai/src/inspect_ai/tool/_tool_support_helpers.py†L171-L198〗
  - `src/inspect_agents/tools.py` — `_log_tool_event` structure and redaction/truncation behavior. 〖F:src/inspect_agents/tools.py†L56-L79〗
- Greppables: `_ensure_sandbox_ready(`, `files:sandbox_preflight`, `INSPECT_AGENTS_FS_MODE`, `text_editor(`, `bash_session(`.
- Pattern references:
  - Preflight warning (one-time structured log) site. 〖F:src/inspect_agents/tools_files.py†L81-L88〗
- Dependencies: none new. Rely on existing Inspect helpers; do not add Docker.

## Scope Definition
- Add env toggle `INSPECT_SANDBOX_PREFLIGHT` with values:
  - `auto` (default): existing behavior — check once, warn on failure, fall back to Store.
  - `skip`: do not execute helper; log once “skipped by config”; treat as unavailable (force Store path).
  - `force`: execute helper and on failure raise `PrerequisiteError` (no fallback).
- Implement entirely inside `src/inspect_agents/tools_files.py` (env parsing + `_ensure_sandbox_ready` branching). No signature changes.
- Do not modify tool APIs or introduce Docker requirements.

## Success Criteria
- Behavior checks:
  - Default (unset/auto): unchanged; first sandbox call logs one warning on failure and falls back.
  - `skip`: sandbox paths never attempted; Store fallback used silently except for one info log.
  - `force`: first sandbox call raises `PrerequisiteError` when unavailable; with in-process stubs, calls succeed.
- Tests (new): focused unit tests validating each mode using existing stubbing pattern (see tests prompt). Must run offline.
- Performance: after initial branch decision, no added awaits on hot paths; logs emitted once per process.


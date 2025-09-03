# TODO — Unit Tests for Preflight Modes, Reset, and Logging

## Context & Motivation
- Purpose: ensure preflight behaviors are deterministic and Docker-free in CI across modes (`auto|skip|force`), reset API, and optional logging fields.
- Problem: regressions could reintroduce Docker coupling or hide misconfigurations.
- Impact: reliable CI with explicit coverage; protects developer experience.

## Implementation Guidance
- Existing test patterns:
  - In-process stubs for editor and bash-session live in `tests/unit/inspect_agents/test_fs_sandbox.py` (install into `sys.modules`). 〖F:tests/unit/inspect_agents/test_fs_sandbox.py†L8-L13〗 〖F:tests/unit/inspect_agents/test_fs_sandbox.py†L18-L28〗 〖F:tests/unit/inspect_agents/test_fs_sandbox.py†L70-L78〗
- Add: `tests/unit/inspect_agents/test_sandbox_preflight_modes.py` with cases:
  1) `skip` mode: `INSPECT_SANDBOX_PREFLIGHT=skip`, `INSPECT_AGENTS_FS_MODE=sandbox`; verify calls fall back to Store (no exceptions), and one info log “skipped by config”.
  2) `force` mode: no stubs; expect `PrerequisiteError` on first sandboxed call (e.g., `read_file()`); then install stubs, call again — succeeds.
  3) default/auto: unset env; no stubs; one warn log with guidance, Store fallback used.
  4) reset API: start unavailable → `reset_sandbox_preflight()` → install stubs → next call uses sandbox path; assert flip.
  5) logging context: set `INSPECT_SANDBOX_LOG_PATHS=1`; assert `cwd_basename` (and other fields) appear in the one-time log.
- Related functions/tools:
  - `read_file()`, `write_file()`, `edit_file()`, `ls()` from `src/inspect_agents/tools.py` (wrappers). 〖F:src/inspect_agents/tools.py†L520-L585〗 〖F:src/inspect_agents/tools.py†L463-L500〗
  - Preflight helper in `src/inspect_agents/tools_files.py` (target of reset).

## Scope Definition
- Create a new test module; reuse and/or factor common stub installers if needed.
- Keep tests offline and fast; no Docker; rely solely on stubs and environment flags.
- Avoid changing production code beyond necessary exports (if reset function is added).

## Success Criteria
- `CI=1 NO_NETWORK=1 PYTHONPATH=src:external/inspect_ai pytest -q -k sandbox` passes locally.
- Logs captured exactly once per process per scenario; assertions stable across platforms.
- Failing modes show clear `PrerequisiteError` trace when in `force` mode.


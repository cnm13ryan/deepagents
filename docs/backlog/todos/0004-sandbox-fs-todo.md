# TODO — Filesystem Sandbox & Safety Work Items (ADR-0004)

Context: Follow-ups derived from ADR 0004 (docs/adr/0004-filesystem-sandbox-guardrails.md) to harden sandbox FS behavior while preserving current defaults. Each section is self-contained and actionable for implementation.

Owner: Core Inspect Agents
Last Updated: 2025-09-03

---

## 1) Sandbox FS Root Confinement

- Context & Motivation
  - [ ] Constrain file access to a configured root in sandbox mode to mitigate traversal/escape risks.
  - [ ] Business value: reduces blast radius; clarifies audit boundary; predictable behavior in CI.

- Implementation Guidance
  - Files: `src/inspect_agents/tools_files.py`, `src/inspect_agents/tools.py`
  - Grep: `_use_sandbox_fs`, `execute_read(`, `execute_write(`, `execute_edit(`, `execute_ls(`, `text_editor(`, `bash_session(`
  - Tasks
    - [ ] Add `_fs_root()` helper (env `INSPECT_AGENTS_FS_ROOT`, default `/repo`).
    - [ ] Enforce absolute path + prefix check for read/write/edit (sandbox branch only).
    - [ ] `ls`: pass explicit root to bash (`ls -1 <root>`) or post-filter results to root.
    - [ ] Raise `ToolException` with clear guidance on allowed root.

- Scope Definition
  - [ ] Modify only sandbox paths in `tools_files.py`; do not change store-backed logic.
  - [ ] Avoid realpath; conservative prefix policy is acceptable (documented in ADR).

- Success Criteria
  - [ ] Allowed: `/repo/a.txt` works; Disallowed: `/etc/passwd` and relative paths reject.
  - [ ] Tests in `tests/unit/inspect_agents` cover allowed/disallowed; use existing stubs.
  - [ ] No behavior change in store mode.

---

## 2) Symlink Denial Preflight (Sandbox)

- Context & Motivation
  - [ ] Prevent symlink abuse when operating in sandbox mode.

- Implementation Guidance
  - Files: `src/inspect_agents/tools_files.py`
  - Grep: `bash_session(`, `anyio.fail_after(`
  - Tasks
    - [ ] Add `_deny_symlink(path)` using `bash_session(action="run", command="test -L <path> && echo SYMLINK || echo OK")` with timeout.
    - [ ] On `SYMLINK` or command failure → raise `ToolException`.
    - [ ] Call from sandbox branches of read/write/edit prior to `text_editor`.

- Scope Definition
  - [ ] Sandbox-only; no store-mode changes.

- Success Criteria
  - [ ] Unit tests extend `test_fs_sandbox.py` with bash stub returning `SYMLINK` for a target path; expect denial.

---

## 3) Byte Ceilings for Read/Write/Edit

- Context & Motivation
  - [ ] Cap payload sizes to avoid OOM/latency stalls.

- Implementation Guidance
  - Files: `src/inspect_agents/tools_files.py`
  - Grep: `INSPECT_AGENTS_TOOL_TIMEOUT`, `_use_sandbox_fs`, `text_editor(`, `bash_session(`
  - Tasks
    - [ ] Add `_max_bytes()` helper (env `INSPECT_AGENTS_FS_MAX_BYTES`, default 5_000_000).
    - [ ] Enforce write/edit argument lengths locally; deny with sizes in message.
    - [ ] Read (sandbox): preflight byte size via `wc -c <file>` using `bash_session`; deny if over cap.
    - [ ] Read (store): check `len(content)` similarly.

- Scope Definition
  - [ ] Deny rather than truncate by default; document behavior.

- Success Criteria
  - [ ] Tests for oversized write/edit/read in both modes; no content leaks in logs.

---

## 4) Read-Only Mode Flag

- Context & Motivation
  - [ ] Provide an audit-friendly mode preventing mutations globally.

- Implementation Guidance
  - Files: `src/inspect_agents/tools_files.py`
  - Grep: `execute_write(`, `execute_edit(`, `execute_delete(`
  - Tasks
    - [ ] Add `_readonly()` helper (env `INSPECT_AGENTS_FS_READONLY`).
    - [ ] Short-circuit write/edit/delete with `ToolException` when enabled; include guidance to unset flag.

- Scope Definition
  - [ ] Applies to store and sandbox; delete remains unsupported in sandbox.

- Success Criteria
  - [ ] Tests parametrize env; writes/edits/deletes fail; reads still succeed.

---

## 5) Safer Edit: expected_count + dry_run

- Context & Motivation
  - [ ] Reduce accidental broad edits; allow preview.

- Implementation Guidance
  - Files: `src/inspect_agents/tools_files.py`, `src/inspect_agents/tools.py`
  - Grep: `class EditParams`, `execute_edit(`, `def edit_file():`
  - Tasks
    - [ ] Extend `EditParams` with `expected_count: int | None` and `dry_run: bool = False`.
    - [ ] Store mode: count `content.count(old_string)`; enforce `expected_count`; if `dry_run`, return summary without mutation.
    - [ ] Sandbox: pre-read via `text_editor('view')` to count; enforce `expected_count`; skip `str_replace` in `dry_run`.
    - [ ] Update wrapper `edit_file()` to expose new params.

- Scope Definition
  - [ ] Backward compatible defaults (no new args required by callers).

- Success Criteria
  - [ ] Tests for match/mismatch and dry-run in both modes; store content unchanged on dry-run.

---

## 6) Observability Hygiene (No Content in Logs)

- Context & Motivation
  - [ ] Avoid leaking file content via tool_event logs.

- Implementation Guidance
  - Files: `src/inspect_agents/tools_files.py`, verify helper in `src/inspect_agents/tools.py`
  - Grep: `_log_tool_event(` for files:write/edit/read branches
  - Tasks
    - [ ] Replace content-bearing args with metadata only (e.g., `content_len`, `old_len`, `new_len`).
    - [ ] Keep file paths, offsets, limits, counts; no raw contents.

- Scope Definition
  - [ ] Do not modify logging framework; only per-call args.

- Success Criteria
  - [ ] caplog-based test asserts content strings absent; lengths present.

---

## 7) Documentation Surfacing (Link ADR + Docstrings)

- Context & Motivation
  - [ ] Make safety posture obvious in entry-point docs and tool docstrings.

- Implementation Guidance
  - Files: `docs/inspect_agents_quickstart.md`, `docs/tool-umbrellas.md`, `src/inspect_agents/tools_files.py`
  - Grep: `INSPECT_AGENTS_FS_MODE`, `Security Notes:`
  - Tasks
    - [ ] Link ADR-0004 from Quickstart and Tool Umbrellas.
    - [ ] Add concise Security Notes bullets in `files_tool` docstring and per-op execute_* docstrings.
    - [ ] List proposed envs (FS_ROOT, FS_MAX_BYTES, FS_READONLY) as “proposed” until enforced.

- Scope Definition
  - [ ] Documentation-only; no behavior change.

- Success Criteria
  - [ ] Docs render with cross-links; CI/lint unaffected.

---

## 8) Sandbox `ls` Rooting / Post-Filter

- Context & Motivation
  - [ ] Ensure `ls` behavior is stable and respects configured root.

- Implementation Guidance
  - Files: `src/inspect_agents/tools_files.py`
  - Grep: `execute_ls(`, `bash_session(`
  - Tasks
    - [ ] Option A: `ls -1 <FS_ROOT>`; Option B: change working dir or post-filter results to within root.
    - [ ] Update sandbox bash stub in tests to accept root argument and return scoped list.

- Scope Definition
  - [ ] Sandbox-only change; keep store mode intact.

- Success Criteria
  - [ ] Unit tests validate ls returns items under FS_ROOT only; deterministic ordering.

# ADR 0004: Filesystem Sandbox Mode — Guardrails and Defaults

Status: Accepted (documentation-only; enforcement for some items is proposed)

Date: 2025-09-03

## Context

Deepagents provides file tools that are Store-backed by default and can optionally operate on a host filesystem when `INSPECT_AGENTS_FS_MODE=sandbox`. In sandbox mode, the tools proxy to Inspect’s `text_editor` (for read/write/edit) and `bash_session` (for ls). When the sandbox transport is unavailable, the tools fall back to Store mode with a clear, logged warning.

Current behavior (as implemented):
- Default mode is `store`; sandbox mode is opt-in via `INSPECT_AGENTS_FS_MODE`.  
- In sandbox mode, `read` → `text_editor('view')`, `write` → `text_editor('create')`, `edit` → `text_editor('str_replace')`; `ls` → `bash_session('run', 'ls -1')`.  
- If sandbox checks fail, tools fall back to Store-backed operations (no host FS writes).  
- `delete` is intentionally unsupported in sandbox mode; only available in Store-backed mode.

## Problem

Operating on a host filesystem introduces risks (path traversal, symlink abuse, accidental destructive edits, large-file stalls, and content leakage via logs). We need clear guidance and recommended defaults that align with deepagents’ safety-first design, without forcing consumers to adopt heavy guardrails before they are implemented.

## Decision

Document a security baseline and recommended defaults for sandbox FS operations, while keeping code behavior unchanged for now. These notes guide usage and pave the way for incremental enforcement.

### Security Baseline (documented behavior today)
- Optional sandbox mode, Store-backed by default.
- Graceful fallback to Store when sandbox support is unavailable.
- `delete` disabled in sandbox mode.
- Per-call timeouts via `INSPECT_AGENTS_TOOL_TIMEOUT` to prevent hangs.
- Structured logging with argument redaction and length caps for observability.

### Recommended Guardrails (proposed for future enforcement)
- Root confinement: resolve real paths and deny access when a path escapes a configured root (e.g., `INSPECT_AGENTS_FS_ROOT`).
- Symlink policy: deny or very carefully handle symlinks (prefer `lstat`/realpath checks; avoid following symlinks by default).
- Size limits: enforce byte ceilings for read/write/replace operations (e.g., `INSPECT_AGENTS_FS_MAX_BYTES`).
- Atomicity: prefer temp-write + atomic rename on host FS; document backend limitations when atomicity is not guaranteed.
- Idempotency/safety for `str_replace`: add optional preimage checks and an `expected_count` parameter to prevent unintended broad edits.
- Observability hygiene: default to path-only logs; never log file contents; if sampling is enabled, cap and redact aggressively.
- Read-only mode: provide an opt-in read-only flag for audit workflows.

## Rationale

These recommendations follow deepagents’ design principles:
- Safe-by-default, opt-in to heavier capabilities.  
- Graceful degradation and deterministic tests (stubs for sandbox tools).  
- Minimal surface area wrappers with lazy imports and clear docstrings.  
- Typed results behind an env flag, not required by default.

## Environment Variables

Existing:
- `INSPECT_AGENTS_FS_MODE`: `store` (default) or `sandbox`.
- `INSPECT_AGENTS_TOOL_TIMEOUT`: per-call timeout in seconds (default 15).
- `INSPECT_AGENTS_TYPED_RESULTS`: enable typed result models for tools.

Proposed (documentation guidance; not yet enforced):
- `INSPECT_AGENTS_FS_ROOT`: absolute path confining sandbox file operations.
- `INSPECT_AGENTS_FS_MAX_BYTES`: hard cap for read/write/replace payloads.

## Consequences

- Clear guidance reduces foot-guns when users enable sandbox mode.
- Proposed flags create a migration path for enforcement without breaking existing users.
- Keeping `delete` disabled in sandbox minimizes accidental host damage.

## Alternatives Considered

- Full enforcement now: rejected due to scope and compatibility risk; we prefer phased adoption backed by tests.
- Rely entirely on external sandbox guarantees: insufficient for defense in depth (symlinks, traversal still relevant).

## Rollout & Testing

- Documentation-only in this change. Existing unit tests cover sandbox routing and fallback. Future enforcement will add unit tests for root confinement, symlink denial, and size ceilings.

## Future Work

- Implement root confinement and symlink policy with tests.
- Add `expected_count` and optional dry-run preview for `str_replace`.
- Provide read-only mode and per-call overrides for expert workflows.


# Design Note — Sandbox FS Preflight & Fallback

Context
- File tools switch to Inspect’s sandbox-backed `text_editor`/`bash_session` when `INSPECT_AGENTS_FS_MODE=sandbox`.
- In some environments (CI, local without Docker), the `inspect-tool-support` service is not present.
- Goal: surface helpful guidance once, then gracefully fall back to Store-backed FS without breaking tests or examples.

Current Behavior (implemented)
- A cached async preflight runs on first sandbox use. It:
  - Checks for in-process stubs (unit tests) and short-circuits to “available”.
  - Attempts `tool_support_sandbox(<tool>)`; on success, marks sandbox available.
  - On failure, logs a one-time structured warning containing the upstream `PrerequisiteError` guidance, then falls back to Store FS.
- Calls in ls/read/write/edit are gated by this preflight.

Open Questions & Options

1) Preflight Mode Toggle
- auto (default): preflight once; fallback on failure with warning.
- skip: never check; treat as unavailable; direct Store path; one-time “skipped by config” info.
- force: require sandbox; if unavailable, raise `PrerequisiteError` with guidance.
Pros: power/users get control; CI can skip; prod can enforce. Cons: misconfig can surprise; support load.

2) Cache Scope & Refresh
- Sticky cache (process-wide): simplest and zero overhead after first call; stale if sandbox appears mid-run.
- TTL cache: recheck every N seconds (e.g., 300s) and log a status-change once if availability flips.
- Explicit reset: expose `reset_sandbox_preflight()` for long-lived services/tests.
Trade-off: TTL adds complexity; explicit reset is simpler and predictable.

3) Warning Context Details
- Default minimal fields: `{tool: files:sandbox_preflight, phase: warn, ok: false, reason, fs_mode}` plus upstream text.
- Path details are potentially sensitive; make them opt-in: `INSPECT_SANDBOX_LOG_PATHS=1` to include cwd basename or VCS root relpath if detected.
Trade-off: better triage vs. PII/noise in shared logs.

Recommended Direction
- Keep default `auto` behavior with a sticky cache for simplicity and zero hot-path overhead.
- Add an explicit `force` mode for strict prod and a `skip` mode for constrained/offline CI.
- Provide an explicit `reset` helper; defer TTL unless a real use case emerges.
- Keep warnings minimal-by-default; add opt-in path context behind an env flag.

Proposed Environment Variables (not all implemented yet)
- `INSPECT_SANDBOX_PREFLIGHT=auto|skip|force` (default: auto)
- `INSPECT_SANDBOX_LOG_PATHS=0|1` (default: 0)
- `INSPECT_SANDBOX_PREFLIGHT_TTL=<seconds>` (optional; default unset for sticky cache)

Rationale & Alignment
- Matches project patterns: env-driven behavior, conservative defaults, lazy imports, graceful fallbacks, and testability without Docker.
- One-time structured logging integrates with existing `_log_tool_event` semantics and redaction/truncation.


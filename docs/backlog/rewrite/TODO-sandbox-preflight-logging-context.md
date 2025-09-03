# TODO — Opt-In Warning Context (INSPECT_SANDBOX_LOG_PATHS)

## Context & Motivation
- Purpose: enrich the one-time preflight warning with minimal, non-sensitive context for faster triage in shared logs.
- Problem: current warning lacks environment context; harder to correlate across repos/services.
- Impact: quicker root-cause in multi-repo setups while keeping safe-by-default logging.
- Constraints: never leak sensitive paths by default; maintain current redaction/truncation.

## Implementation Guidance
- Files to examine:
  - `src/inspect_agents/tools_files.py` — preflight logging site and payload. 〖F:src/inspect_agents/tools_files.py†L81-L88〗
  - `src/inspect_agents/tools.py` — `_log_tool_event` expectations and truncation. 〖F:src/inspect_agents/tools.py†L56-L79〗
- Greppables: `files:sandbox_preflight`, `_log_tool_event(`, `INSPECT_AGENTS_FS_MODE`.
- Add optional fields when `INSPECT_SANDBOX_LOG_PATHS=1`:
  - `fs_mode`, `tool_name`, `reason` (helper_missing|prereq_error), `code:"SBOX-MISS-01"`.
  - `cwd_basename = os.path.basename(os.getcwd())`. If you detect a VCS root, include a relative path key (optional).

## Scope Definition
- Modify only the logging payload in `_ensure_sandbox_ready`; defaults remain minimal.
- No changes to `_log_tool_event` or global logging config.

## Success Criteria
- With env disabled/default: warning unchanged (minimal fields).
- With `INSPECT_SANDBOX_LOG_PATHS=1`: includes additional fields; appears once per process.
- Tests (new): capture logs with `caplog` and assert presence/absence of fields under both settings.


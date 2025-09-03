# Observability Hygiene — Open Questions

Context: We tightened tool_event logging for file operations so that arguments never include raw content and only log metadata/lengths. The current implementation logs:
- files:write — {file_path, content_len, instance}
- files:edit — {file_path, old_len, new_len, replace_all, instance}
- files:read — {file_path, offset, limit, instance}

Backstops remain in place: _redact_and_truncate() applies key redaction and length-based truncation, and approval/logging layers already redact keys like content and file_text. We maintained return values; only observability payloads changed.

Below are open questions requiring a decision to finalize verification and harden against regressions.

---

## 1) How should we enable tests in this environment?

Problem
- Unit tests that validate logging hygiene (tests/unit/inspect_agents/test_tool_observability.py) are async and require pytest-asyncio (or anyio). In this environment, network/package install attempts (uv or pip) are blocked by sandbox/SSL errors, so the tests cannot run.

Options
- Option A: Allow uv to run with a writable cache (e.g., UV_CACHE_DIR=.uv-cache) and network access to fetch pytest-asyncio/anyio. Minimal change; uses existing test suite.
- Option B: Permit creating a local venv in-repo and installing pytest-asyncio/anyio via pip. Similar to A, but under a normal venv.
- Option C: Add a temporary smoke test (no external deps) that runs the files tools under anyio’s built-in runner or asyncio loop and asserts that tool_event args include only *_len fields and never raw content. Remove once CI runs the real suite.

Recommendation
- Prefer Option A for lowest friction and parity with CI. If network remains restricted, Option C provides on-box verification without new dependencies.

Decision Needed
- Which option should we pursue to validate in this environment? Target: decide before merging related changes so we can attach test evidence.

---

## 2) Add a defensive guard inside `_log_tool_event`?

Problem
- Today, enforcement occurs at call sites for files tools. Future tools (or regressions) might accidentally pass raw strings (e.g., content, file_text, old_string, new_string) to _log_tool_event.

Option
- Add a lightweight normalization in _log_tool_event that, before redaction/truncation, rewrites known keys:
  - content → content_len
  - file_text → file_text_len
  - old_string/new_string → old_len/new_len
  - and strips the original string values

Pros/Cons
- Pros: Belt-and-suspenders defense; prevents accidental leaks from new callers.
- Cons: Slight implicit behavior; may mask incorrect usage instead of surfacing it in code review.

Recommendation
- Add the guard with a small allowlist and an INFO comment in code; keep existing call-site hygiene. Also add a test that feeds raw args into _log_tool_event and asserts the normalization.

Decision Needed
- Should we add this normalization now, or keep call-site-only guarantees?

---

## 3) Repository-wide regression check for logs

Problem
- Even with call-site hygiene and backstops, future changes could reintroduce raw content into tool_event args.

Option
- Add a caplog-based test that scans all tool_event records during a representative tool run set and fails if any args contain very long strings (e.g., > N chars) or the known sensitive keys (content, file_text) with string values. Keep thresholds modest to avoid false positives.

Recommendation
- Add a single, fast unit test in tests/unit/inspect_agents that exercises files:read/write/edit and asserts only *_len fields are present. Optionally generalize to all tools in a smoke pass.

Decision Needed
- Do we want this repository-wide guard as part of the default unit test run?

---

Notes
- Scope remains limited to observability payloads; functional behavior and return types are unchanged. Redaction/truncation remains as a backstop.


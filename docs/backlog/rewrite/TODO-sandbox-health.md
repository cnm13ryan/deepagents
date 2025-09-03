# TODO — Sandbox Readiness Check

Context & Motivation
- When host FS mode is enabled, the `text_editor` tool depends on an `inspect-tool-support` service in the sandbox. Provide a preflight check and graceful fallbacks.

Implementation Guidance
- Tool support: `external/inspect_ai/src/inspect_ai/tool/_tool_support_helpers.py` (`tool_support_sandbox`, `PrerequisiteError` guidance)

Scope — Do
- [ ] Add a preflight health check that verifies sandbox service availability
- [x] In tests, stub or mock sandbox transport; avoid Docker requirement in CI
- [x] On missing sandbox, fall back to Store-backed FS with a clear warning

Scope — Don’t
- Don’t hard-require Docker in CI examples/tests

Success Criteria
- [ ] Health check surfaces helpful guidance; examples either find sandbox or gracefully fall back

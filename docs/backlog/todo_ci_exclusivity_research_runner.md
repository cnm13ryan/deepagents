# TODO — Apply Exclusivity in CI for the Research Runner

Context & Motivation
- Purpose: Make CI runs deterministic by enforcing single‑handoff behavior.
- Problem: `examples/research/run_local.py` only added exclusivity for `dev`/`prod`; CI remained permissive. This caused non‑determinism when a turn emitted multiple tools including a handoff.
- Impact: Stabilizes automated test/demo workflows by ensuring only the first handoff executes in a turn under `--approval ci`.

Implementation Guidance
- File: `examples/research/run_local.py` — extend the conditional that appends `handoff_exclusive_policy()` to include `"ci"`.
- Grep terms: `--approval`, `approval_preset`, `handoff_exclusive_policy`.
- Pattern: Preserve default behavior when `--approval` is not supplied.

Scope Definition
- Implement: Change the conditional to also include `ci`.
- Avoid: Changing presets in library code or default behavior without `--approval`.
- Integrations: None outside this file.

Success Criteria
- Behavior: Running with `--approval ci` appends `handoff_exclusive_policy()`; transcripts show only the first handoff executes if multiple tools were proposed.
- Tests: Integration test exercises the runner with a toy model, patches approvals, and asserts the exclusivity sentinel is present.
- Docs: Open questions captured in `docs/design/open-questions.md`.

Task Checklist
- [x] Patch runner to append exclusivity for `ci`. 〖F:examples/research/run_local.py†L187-L193〗
- [x] Add targeted test `tests/research/test_run_local_exclusive_ci.py` asserting exclusivity is applied. 〖F:tests/research/test_run_local_exclusive_ci.py†L1-L40〗 〖F:tests/research/test_run_local_exclusive_ci.py†L42-L76〗
- [ ] Optional: Note `--approval ci` determinism in `examples/research/README.md`.
- [x] Record related design questions in `docs/design/open-questions.md`.

Owner
- Eng: @you (temporary)

Status
- DONE (2025-09-04) — code + tests landed; docs note optional.

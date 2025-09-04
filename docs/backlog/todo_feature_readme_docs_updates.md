# TODO: Docs Adjustments — Supervisor Tool Exposure & ADR 0004 Baseline

## Context & Motivation
- Purpose: remove doc/code drift around built‑in tool exposure and filesystem guardrails.
- Problems:
  - Supervisor exposes wrapper tools (`ls/read_file/write_file/edit_file`) by default, not the unified `files` tool; docs should state this explicitly.
  - ADR 0004 lists root confinement and symlink denial as “recommended”; code enforces them in sandbox flows. Promote to documented baseline.
- Value: consistent expectations for users and reviewers.

## Implementation Guidance
- Examine: `docs/tools/README.md` and `docs/tools/files.md` (exposure defaults and concurrency notes), `docs/adr/0004-filesystem-sandbox-guardrails.md` (baseline vs recommended sections).
- Grep tokens: “Built-in tools”, `files` vs wrappers, “root confinement”, “symlink”.

## Scope Definition
- Implement: add one‑line note under wrappers and in README clarifying exposure defaults; update ADR 0004 to promote root confinement + symlink denial to baseline with clarifying language about sandbox vs store.
- Tests: docs build succeeds; links valid.

## Success Criteria
- Docs: published pages reflect accurate exposure defaults and baseline guardrails.

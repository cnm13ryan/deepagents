# Backlog Index

Last updated: 2025-09-04

Curated index of all items under `docs/backlog/`, grouped for quick navigation. This index is non‑destructive: it does not move or rename files to avoid breaking links. Use it to find the right TODO quickly.

## How To Use
- New item: add a `todo_feature_<short-name>.md` with sections: Context & Motivation, Implementation Guidance, Scope Definition, Success Criteria.
- Cross‑link related items and note overlaps (see “Overlaps” below) instead of duplicating content.
- Keep titles starting with `# TODO:` for consistency and scanability.

## Categories

### Approvals & Handoffs (ADR‑0005) — sorted by name
- [Apply Exclusivity in CI for the Research Runner](./todo_ci_exclusivity_research_runner.md) — overlaps with the next item; see Overlaps.
- [Approvals Presets — Add Handoff Exclusivity by Default (dev/prod)](./todo_feature_approvals_handoff_exclusivity_default.md)
- [Research Runner — Apply Handoff Exclusivity in CI](./todo_feature_runner_ci_exclusive.md)
- [Transcripts — Standardized “Skipped Due to Handoff” ToolEvent](./todo_feature_transcript_skipped_tool_event.md)

### Config & YAML — sorted by name
- [Model Roles Map — Implementation Checklists](./TODO-model-roles-map.md)
- [YAML Config — Add Role Mapping for Sub‑Agents](./todo_feature_yaml_subagent_role_mapping.md)
- [YAML Limits — Parse and Return Inspect Limits](./todo_feature_yaml_limits_parser.md)

### Filesystem Sandbox (ADR‑0004) — sorted by name
- [Filesystem Sandbox — Enforce Read‑Only Mode Flag](./todo_feature_fs_readonly_flag.md)
- [Docs Adjustments — Supervisor Tool Exposure & ADR 0004 Baseline](./todo_feature_readme_docs_updates.md)

### Iterative Agent & Pruning — sorted by name
- [Iterative Agent — `code_only` Flag](./todo_feature_iterative_code_only.md)
- [Iterative Agent — Env Fallbacks for Time/Steps](./todo_feature_iterative_env_fallbacks.md)
- [Iterative Agent — Add `max_messages`](./todo_feature_iterative_max_messages.md)
- [Conversation Pruning — Env Toggles + Optional Debug Log](./todo_feature_pruning_env_toggles.md)
- [Token‑Aware Pruning (Optional)](./todo_feature_pruning_token_aware.md)
- [Iterative Task (Inspect) — `enable_web_search` Flag](./todo_feature_iterative_task_web_search_flag.md)

### Eval Logs Tooling (`scripts/read_log_eval.py`) — sorted by name
- [Summary Stats and `summary.json`](./todo_feature_read_log_eval_summary.md)
- [`--out-dir` and Sidecar Mode](./todo_feature_read_log_eval_out_dir.md)
- [JSONL/Parquet Export Options](./todo_feature_read_log_eval_formats.md)
- [Log Selection Filters](./todo_feature_read_log_eval_filters.md)

### Retries & Cache — sorted by name
- [Retry Policy — Feature](./todo_feature_retry_policy.md)
- [Retry/Cache Tests — Feature](./todo_feature_retry_cache_tests.md)
- [Cache Policy — Feature](./todo_feature_cache_policy.md)

### Epics & Misc
- [Rewrite Epic](./rewrite/README.md)
- [General Todos](./todos/README.md)

## Overlaps / Duplicates
- CI exclusivity for the research runner is tracked in both:
  - `todo_feature_runner_ci_exclusive.md` and
  - `todo_ci_exclusivity_research_runner.md` (older, includes checklist/status).
  Prefer the `todo_feature_…` file for new work; link or consolidate later when convenient.

## Conventions
- File naming: `todo_feature_<area>_<topic>.md`; epics in subfolders.
- Title: start with `# TODO:` followed by a crisp scope.
- Sections: Context & Motivation, Implementation Guidance, Scope Definition, Success Criteria.
- Status/Owner: optional at the end of the file.

# TODO: read_log_eval.py — Log Selection Filters

## Context & Motivation
- Purpose: select logs by time window or name prefix for listing and analysis.
- Problem: only explicit `--file` or the latest file is supported; large log directories are unwieldy.
- Value: faster selection, better scripting.

## Implementation Guidance
- Examine: `scripts/read_log_eval.py` (`_list_eval_logs`, `_pick_latest_eval`, CLI parsing).
- Grep tokens: `--list`, `--file`, `glob("*.eval")`, `st_mtime`.

## Scope Definition
- Implement: add `--since`, `--until` (ISO `YYYY-MM-DDThh:mm` accepted), `--prefix`, and `--limit N`. Apply filters to `--list` and to the default latest selection when `--file` isn’t provided.
- Tests: create several dummy `.eval` files with varied mtimes and prefixes; assert selection behavior matches filters.

## Success Criteria
- Behavior: filters applied consistently across both listing and analysis paths.
- Tests: pass offline.

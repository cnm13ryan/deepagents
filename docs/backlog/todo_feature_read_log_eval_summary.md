# TODO: read_log_eval.py — Summary Stats and summary.json

## Context & Motivation
- Purpose: provide at‑a‑glance metrics and machine‑readable summary for downstream tooling.
- Problem: script prints only `.head()` previews and writes CSVs to CWD.
- Value: faster triage and integration.

## Implementation Guidance
- Examine: `scripts/read_log_eval.py` (`_analyze`), pandas exports.
- Grep tokens: `print( ... head() )`, `.to_csv(`, argparse parser.

## Scope Definition
- Implement: add `--summary/--no-summary` (default on). Compute simple aggregates (counts, unique tasks, error rates if columns present, basic timing stats); print a concise console block; write `summary.json` with schema `{counts, columns_present, notes}`.
- Tests: monkeypatch DataFrames or produce a tiny temp log; assert file creation and fields.

## Success Criteria
- Behavior: summary printed and JSON written alongside CSVs (or per `--out-dir`).
- Tests: pass offline.

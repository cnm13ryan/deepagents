# TODO: read_log_eval.py — JSONL/Parquet Export Options

## Context & Motivation
- Purpose: preserve nested fields and support analytics workflows.
- Problem: CSV can be lossy; consumers often want JSONL or Parquet.
- Value: better interoperability with data tools.

## Implementation Guidance
- Examine: `scripts/read_log_eval.py` (export sites).
- Grep tokens: `.to_csv(`, argparse parser.
- Deps: JSONL via pandas; Parquet behind optional `pyarrow` or `fastparquet` with graceful fallback.

## Scope Definition
- Implement: add `--format csv,jsonl[,parquet]` multi‑select (default `csv`). Write each table per requested formats.
- Tests: assert JSONL line counts; Parquet gracefully skipped with a clear message when deps absent.

## Success Criteria
- Behavior: requested formats emitted; clear messaging when Parquet unavailable.
- Tests: pass offline.

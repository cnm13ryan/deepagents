# TODO: read_log_eval.py — `--out-dir` and Sidecar Mode

## Context & Motivation
- Purpose: control where artifacts are written; keep outputs organized.
- Problem: CSVs are always written to CWD.
- Value: better scripting and hygiene.

## Implementation Guidance
- Examine: `scripts/read_log_eval.py` (CSV writes, arg parsing).
- Grep tokens: `.to_csv(`, `argparse.ArgumentParser(`.

## Scope Definition
- Implement: add `--out-dir <path>` (default `.`). Special value `same` writes next to the `.eval` file inside `INSPECT_LOG_DIR`. Ensure directory exists; create if missing.
- Tests: write to `tmp_path`, assert file presence and paths.

## Success Criteria
- Behavior: artifacts written to requested location.
- Tests: pass offline.

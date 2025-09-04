# inspect log — Query, read, and convert logs

Utilities for listing logs, printing them as JSON, and converting between formats.

## Subcommands

- `log list` — List logs in `--log-dir` (filter by status, absolute paths, JSON output).
- `log dump` — Print a log file as JSON; supports `--header-only` and `--resolve-attachments`.
- `log convert` — Convert logs to `eval` or `json` format into an output directory.
- `log schema` — Print the JSON schema for log files.

Hidden (advanced)
- `log headers` — Print headers for one or more log files (fast, no samples).
- `log types` — Print TypeScript declarations for log JSON.

## Examples

```bash
# List all logs (relative paths)
uv run inspect log list

# List only errors and output as JSON (absolute paths)
uv run inspect log list --status error --json --absolute

# Dump a log's header only
uv run inspect log dump logs/run.eval --header-only

# Convert all logs to JSON into ./logs-json
uv run inspect log convert ./logs --to json --output-dir ./logs-json --overwrite
```

## Export Recipes (from Inspect View)

```bash
# Find the log you saw in the viewer
uv run inspect log list --json --absolute | jq '.[0].name'  # pick the right one

# Export that single log to JSON
uv run inspect log dump /abs/path/to/log.eval > eval.json

# Convert an entire log directory to JSON (non‑destructive)
uv run inspect log convert ./logs --to json --output-dir ./logs-json --overwrite

# Create a static viewer bundle + logs (zip or host)
uv run inspect view bundle --output-dir ./logs-www
```

Notes
- Inspect supports two physical formats: compact binary `eval` and `json`. The CLI reads either and emits JSON for analysis.
 - For a ready-to-run export helper, see `scripts/README.md` (script: `scripts/export_eval_json.sh`).

---

See also: `inspect view`, `inspect score`, `inspect info`.

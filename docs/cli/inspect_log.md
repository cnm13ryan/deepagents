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

Notes
- Inspect supports two physical formats: compact binary `eval` and `json`. The CLI reads either and emits JSON for analysis.

---

See also: `inspect view`, `inspect score`, `inspect info`.

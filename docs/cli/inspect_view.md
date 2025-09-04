# Inspect View — Visualize Evaluation Logs

The `inspect view` command launches the Inspect log viewer, a web‑based interface for visualizing and exploring evaluation logs.

## Core Functionality

- Starts a local web server that provides an interactive UI for browsing evaluation logs.
- By default, serves logs from `./logs` and runs on port `7575`.

## Key Features

- **Live viewing**: See real‑time updates as evaluations run, including completed samples and incremental metric calculations.
- **Sample exploration**: Drill into individual samples to view message histories, tool calls, scoring decisions, and metadata.
- **Log history navigation**: Browse all evaluation logs in the directory via a history panel.
- **Filtering and sorting**: Filter samples (e.g., by score) and sort by different criteria.

## Usage

Run the viewer once at the beginning of a session; it automatically updates as new evaluations are written.

```bash
# Default: uses ./logs and port 7575
uv run inspect view

# Specify a different log directory and port
uv run inspect view --log-dir ./experiment-logs --port 6565
```

Common options:
- `--log-dir`: Use an alternate log directory.
- `--port`: Listen on a different port (default 7575).
- `--host`: Bind host (default 127.0.0.1).

Open your browser to http://127.0.0.1:7575 (or your chosen host/port).

## Export and Share Logs

Use these CLI commands to export exactly what you’re viewing:

```bash
# 1) Locate the log you saw in the History panel
#    (or list programmatically)
uv run inspect log list --json --absolute

# 2) Export one log to JSON (works for .eval or .json sources)
uv run inspect log dump /abs/path/to/log.eval > eval.json

# Optional: convert many logs to JSON into a new directory
uv run inspect log convert ./logs --to json --output-dir ./logs-json --overwrite

# 3) Bundle a shareable static viewer + logs (zip or host anywhere)
uv run inspect view bundle --output-dir ./logs-www
```

Notes
- By default, `inspect view` and `inspect log` read from `INSPECT_LOG_DIR` (defaults to `./logs`). Pass `--log-dir` to override.
- `inspect log dump` always emits JSON, regardless of underlying storage format.
- `inspect view bundle` creates a self‑contained site at `./logs-www/` with `index.html`, assets, and a `logs/` folder you can publish.
 - For scripted examples (e.g., exporting a single log to JSON), see `scripts/README.md`.

## Implementation Notes (for contributors)

- The CLI `view` group delegates to `start`, which calls `inspect_ai._view.view()`. That initializes logging, acquires the port (terminating any stale viewer on the same port), and starts the aiohttp server that serves the UI and log APIs.

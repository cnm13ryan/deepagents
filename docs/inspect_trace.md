# inspect trace — List and read execution traces

Work with TRACE-level logs: list recent trace files, dump entries, filter HTTP calls, and highlight anomalies.

## Subcommands

- `trace list [--json]` — List available trace files (last 10 preserved).
- `trace dump [TRACE_FILE] [--filter text]` — Dump a trace file as JSON; optional substring filter on messages.
- `trace http [TRACE_FILE] [--filter text] [--failed]` — Show HTTP requests from the trace; `--failed` shows non-200 responses only.
- `trace anomalies [TRACE_FILE] [--filter text] [--all]` — Show running/cancelled actions; with `--all`, include errors and timeouts.

## Examples

```bash
uv run inspect trace list
uv run inspect trace http --failed
uv run inspect trace anomalies --all
```

Notes
- If a trace file path is not provided, the latest trace is used.
- Relative paths are resolved under the Inspect trace directory.

---

See also: `--log-level trace` and `inspect view` for runtime diagnostics.

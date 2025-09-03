# inspect info — Version and log inspection helpers

Info utilities for Inspect AI: version, and (hidden) log helpers mirroring `inspect log`.

## Subcommands

- `info version` — Print Inspect version and package path; `--json` for machine-readable output.

Hidden (advanced)
- `info log-file PATH [--header-only[=MB]]` — Print a log as JSON (optionally header only; `0` forces header-only).
- `info log-file-headers FILE...` — Print a JSON list of headers for multiple logs.
- `info log-schema` — Print the JSON schema for logs.
- `info log-types` — Print TypeScript declarations for logs.

## Examples

```bash
uv run inspect info version --json
uv run inspect info log-file logs/run.eval --header-only=5
```

---

See also: `inspect log`, `inspect view`.

# inspect list — Discover tasks and logs

List available tasks on disk (by path globs) and, for convenience, list logs (advanced).

## Subcommands

- `list tasks [PATHS...]` — Show tasks discovered via `@task` decorators.
  - Filters: `-F key=value` includes tasks where metadata matches; add `~` to negate (e.g., `-F draft~=true`). Repeatable.
  - Output: `--absolute` for absolute paths; `--json` for machine-readable output.

Hidden (advanced)
- `list logs` — Same as `inspect log list`.

## Examples

```bash
# List tasks under examples/, relative paths
uv run inspect list tasks examples/

# Filter by attribute and emit JSON
uv run inspect list tasks examples/ -F light=true --json

# Absolute file@task entries
uv run inspect list tasks examples/ --absolute
```

---

See also: `inspect eval`, `inspect log list`.

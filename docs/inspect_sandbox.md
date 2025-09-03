# inspect sandbox — Manage sandbox environments

Create and clean up sandbox environments used by tools and tasks.

## Subcommands

- `sandbox cleanup TYPE [ENVIRONMENT_ID]` — Cleanup environments for a sandbox provider (e.g., `docker`). If `ENVIRONMENT_ID` is provided, only that environment is cleaned; otherwise all are cleaned.

## Examples

```bash
uv run inspect sandbox cleanup docker
uv run inspect sandbox cleanup docker my_env_id
```

Notes
- Pair with `inspect eval --sandbox TYPE[:config]` to run evaluations in a sandbox.

---

See also: `inspect eval --sandbox`, `inspect view`.

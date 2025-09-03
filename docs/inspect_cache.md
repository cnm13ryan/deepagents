# inspect cache — Manage model output cache

List cache sizes, prune expired entries, clear caches, and print the cache directory.

## Subcommands

- `cache list` — Show cache usage per model; `--pruneable` lists only entries eligible for pruning.
- `cache prune [--model MODEL...]` — Remove expired entries (all or for specific models).
- `cache clear (--all | --model MODEL...)` — Clear caches. Use `--all` to clear everything or `--model` (repeatable) for specific caches.
- `cache path` — Print the cache directory.

## Examples

```bash
# Show cache sizes
uv run inspect cache list

# Clear specific model caches
uv run inspect cache clear --model openai/gpt-4o --model anthropic/claude-3-7-sonnet-latest

# Prune only expired entries
uv run inspect cache prune
```

Notes
- `--log-level` (via common options) controls verbosity for operations like prune/clear.

---

See also: `inspect eval --cache-*` model options, provider docs.

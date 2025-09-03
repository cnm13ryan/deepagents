# inspect eval-set — Run multiple tasks with retries

Run a set of tasks (and variants) with coordinated retries, optional bundling of logs + viewer, and the full option surface of `inspect eval`.

## Common usage

```bash
# Run a set of tasks with exponential backoff and connection scaling
uv run inspect eval-set examples/evals/*.py \
  --model openai/gpt-4o-mini \
  --retry-attempts 6 --retry-wait 30 --retry-connections 0.5

# Produce a static bundle (viewer + logs) on success
uv run inspect eval-set tasks/*.py --bundle-dir logs-www --bundle-overwrite
```

## Notable options (in addition to `inspect eval` options)

- `--retry-attempts N`: Max retry rounds for the set.
- `--retry-wait seconds`: Base wait; backs off exponentially (capped at 1h).
- `--retry-connections rate`: Reduce `--max-connections` each retry by this rate.
- `--no-retry-cleanup`: Keep failed log files after retries.
- `--bundle-dir DIR`: Bundle the Inspect View app + logs into DIR.
- `--bundle-overwrite`: Overwrite an existing bundle directory.
- `--log-dir-allow-dirty`: Do not fail if `--log-dir` contains non‑set files.

Tip: All `inspect eval` options (models, limits, logging, scoring, sandbox, etc.) are also available to `eval-set`.

---

See also: `inspect eval`, `inspect view bundle`, `inspect log list`.

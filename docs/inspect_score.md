# inspect score — Score a previous evaluation run

Compute scores (or re-score) for an existing log file using a selected scorer, then write results back to the same file or a new one.

## Common usage

```bash
# Score with a specific scorer and overwrite the original
uv run inspect score logs/run.eval --scorer exact_match --overwrite

# Append scorer output to a new file
uv run inspect score logs/run.eval \
  --scorer mypkg/my_scorer -S threshold=0.8 --output-file logs/run-scored.eval
```

## Notable options

- `--scorer name` — Scorer to run (defaults inferred from the log if possible).
- `-S key=value` — Scorer arguments (repeatable) or `--action append|overwrite`.
- Output: `--overwrite` to modify in place; `--output-file` to write a new file.

Behavior
- If the log already includes scores and `--action` is not set, you are prompted to append or overwrite.
- Prints a summary table of scorer metrics and the resulting log path.

---

See also: `inspect eval --no-score`, `inspect log`, `inspect view`.

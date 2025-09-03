# inspect eval — Run a single evaluation task

Run one task against a model (or model roles), control concurrency, logging, retries, scoring, and sandboxing.

## Common usage

```bash
# Run a task (auto-discovers @task in file)
uv run inspect eval path/to/task.py --model openai/gpt-4o-mini

# Pass task args (-T), limit samples, and enable live log sync
uv run inspect eval task.py \
  -T prompt="Write a haiku" --limit 100 --log-shared

# Disable scoring now; score later with `inspect score`
uv run inspect eval task.py --no-score
```

## Key options (non-exhaustive)

- Model: `--model`, `-M key=value`, `--model-config file`, `--model-role name=model`.
- Task: `-T key=value`, `--task-config file`, `--limit N|A-B`, `--sample-id ids`, `--sample-shuffle[=seed]`, `--epochs N`, `--epochs-reducer name`, `--no-epochs-reducer`.
- Concurrency: `--max-samples`, `--max-tasks`, `--max-subprocesses`, `--max-sandboxes`.
- Time/Token limits: `--message-limit`, `--token-limit`, `--time-limit`, `--working-limit`.
- Errors/Retry: `--fail-on-error[=threshold]`, `--no-fail-on-error`, `--continue-on-fail`, `--retry-on-error[=N]`.
- Logging: `--log-level`, `--log-level-transcript`, `--no-log-samples`, `--no-log-realtime`, `--log-images/--no-log-images`, `--log-buffer`, `--log-shared[=seconds]`.
- Scoring: `--no-score`, `--no-score-display`.
- Generation config: `--max-tokens`, `--temperature`, `--top_p`, `--top_k`, `--stop-seqs`, `--seed`, `--best-of`, penalties, logprobs, response schema, batching `--batch[=size|file]`.
- Sandbox & approvals: `--approval file`, `--sandbox type[:config]`, `--no-sandbox-cleanup`.

Notes
- Uses the log directory from `--log-dir` (default `./logs`) and writes logs in the configured format.
- Live viewing works out of the box locally; add `--log-shared` to sync live updates for remote viewers.

---

See also: `inspect eval-set`, `inspect eval-retry`, `inspect view`, `inspect score`.

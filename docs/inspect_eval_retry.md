# inspect eval-retry — Retry failed evaluations from log files

Re-run failed samples from one or more prior log files with fine-grained control over concurrency, logging, and error handling.

## Common usage

```bash
# Retry one log with conservative concurrency and live log sync
uv run inspect eval-retry logs/2024-08-01T10-00-00_task_eval.json \
  --max-samples 8 --log-shared

# Retry multiple logs and lower model API concurrency
uv run inspect eval-retry logs/*.json --max-connections 4
```

## Notable options

- Concurrency: `--max-samples`, `--max-tasks`, `--max-subprocesses`, `--max-sandboxes`.
- Logging: `--log-level`, `--log-level-transcript`, `--no-log-samples`, `--no-log-realtime`, `--log-images/--no-log-images`, `--log-buffer`, `--log-shared[=seconds]`.
- Errors/Retry: `--fail-on-error[=threshold]`, `--no-fail-on-error`, `--continue-on-fail`, `--retry-on-error[=N]`.
- Timeouts & API: `--max-connections`, `--max-retries`, `--timeout`.
- Scoring: `--no-score`, `--no-score-display`.
- Sandbox: `--no-sandbox-cleanup`.

Notes
- Accepts one or more log files; only failed/cancelled work is retried.
- Writes new/retried runs to the active `--log-dir`.

---

See also: `inspect eval`, `inspect view`, `inspect log list`.

# Inspect Console Cheat Sheet

This page explains how to run and navigate the Inspect‑AI console when executing the Vending‑Bench simulation task.

## Quick Run (Preferred)

```bash
uv run inspect eval src/vending_bench/runtime/simulation.py@run_simulation -T days=15 --display rich --log-dir logs
```

- `--display rich` keeps the output clean and readable (the default is `full`).
- `--log-dir logs` ensures logs and artifacts are written under `./logs` in this repo.

Tip: keep Inspect TRACE logs inside the repo for easier debugging:

```bash
INSPECT_TRACE_FILE=logs/inspect_ai/trace.log \
uv run inspect eval src/vending_bench/runtime/simulation.py@run_simulation -T days=15 --display rich --log-dir logs
```

## What You’ll See

- Header: the task name (`run_simulation`) and active model.
- Progress: a single progress row for one “sample” (the entire multi‑day simulation). Days advance within the agent loop and are recorded in the transcript/metrics, not as separate progress rows.
- Footer: small counters (e.g., HTTP, warnings) that update during the run.

The console is a live Rich panel, not a key‑driven TUI. Use flags to tune verbosity and layout.

## Make It Simpler Or More Verbose

- Quieter UI: `--display plain` (simple prints) or `--display log` (minimal).
- More detail on stdout: add `--log-level info` (or `--log-level trace` for deep debugging).
- You can also set `INSPECT_DISPLAY` and `INSPECT_LOG_LEVEL` environment variables.

## Stopping & Errors

- Press `Ctrl+C` to cancel gracefully; partial artifacts remain in `--log-dir`.
- If a model/API call fails, a traceback is shown and the path to the eval log is printed.

## After The Run: Open And Inspect Logs

- List logs in the chosen directory:

```bash
uv run inspect log list --log-dir logs
```

- Dump a log as JSON to the console:

```bash
uv run inspect log dump logs/<your>.eval | jq '.status, .error, .eval.task'
```

- Visual log viewer:

```bash
uv run inspect view start --log-dir logs
```

Open the viewer URL printed in the console to browse transcripts, per‑day notes (e.g., `=== Day N ===`), and final metrics.

## Traces (Timing, HTTP, Errors)

- Keep traces in‑repo: set `INSPECT_TRACE_FILE=logs/inspect_ai/trace.log` before running.
- Explore traces:

```bash
uv run inspect trace list
uv run inspect trace dump logs/inspect_ai/trace.log | jq
```

## Why Vending‑Bench Looks Different

Vending‑Bench runs the entire N‑day simulation as one “sample”. The console shows “1 sample” and a single progress row; days and end‑of‑day summaries are recorded in the transcript and in the final metrics of the `.eval` log.

## Handy Flags

- `--display [full|conversation|rich|plain|log|none]` – choose UI style.
- `--log-dir logs` – write logs into `./logs`.
- `--log-level [info|trace]` – increase console detail.
- `--traceback-locals` – include locals in tracebacks (use only for targeted debugging).
- `-T key=value` – pass task args (e.g., `-T days=30 -T daily_fee=4.0`).

## Ultra‑Minimal Mode (Artifacts Only)

```bash
uv run inspect eval src/vending_bench/runtime/simulation.py@run_simulation \
  -T days=15 --display log --log-level warning --log-dir logs
```

Then inspect artifacts via the viewer or `inspect log dump`.

## Driver Parity & Role‑Specific Bases

The Inspect task and the Python driver share the same runtime and initializer, so both respect:

- Agent model: `AGENT_MODEL`
- Agent base URL: `AGENT_MODEL_LMSTUDIO_BASE_URL` (LM Studio) / `INSPECT_OPENAI_BASE_URL` (OpenAI) / `INSPECT_GEMINI_BASE_URL` (Gemini)
- Simulator model: `ENVIRONMENT_SIMULATOR_MODEL`
- Simulator base URL: `ENVIRONMENT_SIMULATOR_LMSTUDIO_BASE_URL` / `ENVIRONMENT_SIMULATOR_OPENAI_BASE_URL` / `ENVIRONMENT_SIMULATOR_GEMINI_BASE_URL`

Use either:

```bash
uv run inspect eval src/vending_bench/runtime/simulation.py@run_simulation -T days=15
# or
uv run python -m vending_bench.driver --days 15
```

Both paths are equivalent for model/base‑URL behavior.

## Troubleshooting

- "Unable to initialise lmstudio client" or "Connection error"
  - Verify the role-specific LM Studio base URLs point to reachable endpoints and end with `/v1`:
    ```bash
    curl -s "$AGENT_MODEL_LMSTUDIO_BASE_URL/models" | jq length
    curl -s "$ENVIRONMENT_SIMULATOR_LMSTUDIO_BASE_URL/models" | jq length
    ```
  - For local LM Studio, prefer `http://127.0.0.1:<port>/v1`.
  - Capture and read traces for endpoint details:
    ```bash
    INSPECT_TRACE_FILE=logs/inspect_ai/trace.log \
    uv run inspect eval src/vending_bench/runtime/simulation.py@run_simulation -T days=1 --display rich --log-dir logs
    uv run inspect trace dump logs/inspect_ai/trace.log | rg -i "model|error|openai|lmstudio"
    ```


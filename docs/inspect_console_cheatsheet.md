# Inspect Console Cheat Sheet (deepagents Inspect path)

This page explains how to run and navigate the Inspect‑AI console when using the deepagents Inspect path.

## Quick Run (Preferred)

Run the one‑off prompt task provided in this repo:

```bash
uv run inspect eval examples/inspect/prompt_task.py -S prompt="Write a concise overview of LangGraph" --display rich --log-dir logs
```

- `--display rich` keeps the console readable (default is `full`).
- `--log-dir logs` writes logs and artifacts under `./logs`.

Tip: keep Inspect TRACE logs inside the repo for easier debugging:

```bash
INSPECT_TRACE_FILE=logs/inspect_ai/trace.log \
uv run inspect eval examples/inspect/prompt_task.py -S prompt="Write a concise overview of LangGraph" --display rich --log-dir logs
```

## Enable Standard Tools at Runtime

The task loads deepagents Todo/FS tools by default and appends Inspect’s standard tools when enabled via env:

```bash
# Structured thinking
INSPECT_ENABLE_THINK=1 \
uv run inspect eval examples/inspect/prompt_task.py -S prompt="..."

# Web search via Tavily
INSPECT_ENABLE_WEB_SEARCH=1 TAVILY_API_KEY=... \
uv run inspect eval examples/inspect/prompt_task.py -S prompt="..."

# Web search via Google CSE
INSPECT_ENABLE_WEB_SEARCH=1 GOOGLE_CSE_API_KEY=... GOOGLE_CSE_ID=... \
uv run inspect eval examples/inspect/prompt_task.py -S prompt="..."
```

To list tasks in the file:

```bash
uv run inspect list tasks examples/inspect/prompt_task.py
```

## What You’ll See

- Header: task name (`prompt_task`) and active model.
- Progress: a single progress row for one “sample” (your prompt). Tool calls and reasoning stream within that row.
- Footer: small counters (HTTP, warnings) updated live.

The console is a live Rich panel. Use flags to tune verbosity and layout.

## Make It Simpler Or More Verbose

- Quieter UI: `--display plain` (simple prints) or `--display log` (minimal).
- More detail on stdout: add `--log-level info` (or `--log-level trace` for deep debugging).
- You can also set `INSPECT_DISPLAY` and `INSPECT_LOG_LEVEL`.

## Stopping & Errors

- Press `Ctrl+C` to cancel gracefully; partial artifacts remain in `--log-dir`.
- On errors, a traceback is shown and the `.eval` log path is printed.

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

Open the viewer URL printed in the console to browse transcripts and final metrics.

## Traces (Timing, HTTP, Errors)

- Keep traces in‑repo: set `INSPECT_TRACE_FILE=logs/inspect_ai/trace.log` before running.
- Explore traces:

```bash
uv run inspect trace list
uv run inspect trace dump logs/inspect_ai/trace.log | jq
```

## Models & Environment

The task resolves the model using deepagents’ resolver, so it respects these variables:

- `DEEPAGENTS_MODEL_PROVIDER`: `ollama` (default) | `lm-studio` | `openai` | others
- LM Studio: `LM_STUDIO_BASE_URL` (…/v1), `LM_STUDIO_MODEL_NAME`, `LM_STUDIO_API_KEY`
- Ollama: `OLLAMA_MODEL_NAME`, optional `OLLAMA_BASE_URL`/`OLLAMA_HOST`

Environment loading options:

- Run from the repo root to pick up `.env` automatically (Inspect CLI searches upward).
- Central template: `source env_templates/inspect.env` or use the Python runner with `--env-file env_templates/inspect.env` to seed defaults.

## Handy Flags

- `--display [full|conversation|rich|plain|log|none]` – choose UI style.
- `--log-dir logs` – write logs into `./logs`.
- `--log-level [info|trace]` – increase console detail.
- `--traceback-locals` – include locals in tracebacks (targeted debugging only).

## Ultra‑Minimal Mode (Artifacts Only)

```bash
uv run inspect eval examples/inspect/prompt_task.py \
  -S prompt="Write a concise overview of LangGraph" \
  --display log --log-level warning --log-dir logs
```

Then inspect artifacts via the viewer or `inspect log dump`.

## Troubleshooting

- LM Studio connection errors
  - Verify the endpoint ends with `/v1` and is reachable:
    ```bash
    curl -s "${LM_STUDIO_BASE_URL:-http://127.0.0.1:1234/v1}/models" | jq length
    ```
  - Prefer `http://127.0.0.1:<port>/v1` for local LM Studio.
- Web search not available
  - Set provider keys and enable:
    - Tavily: `INSPECT_ENABLE_WEB_SEARCH=1 TAVILY_API_KEY=...`
    - Google CSE: `INSPECT_ENABLE_WEB_SEARCH=1 GOOGLE_CSE_API_KEY=... GOOGLE_CSE_ID=...`
  - Re‑run the task from the repo root (so `.env` is loaded), or export keys in your shell.

# Research Example (Inspect‑AI Runner)

This example uses the Inspect‑AI runner from this repo — no external agent framework code.

## Task vs Runner (which command to use?)

There are two complementary entry points in this repo:

- Inspect task (for `inspect eval`): `examples/inspect/prompt_task.py` exposes an Inspect task via `@task` and can be executed by the Inspect CLI.
- Python runner (this folder): `examples/research/run_local.py` is a standalone Python script that builds and executes a small multi‑agent composition. It is not an Inspect task, so pointing `inspect eval` at this file will fail with: “No inspect tasks were found at the specified paths.”

Common use case example — curate 2025 Quantinuum arXiv papers:

- Inspect task (CLI):
  - `INSPECT_ENABLE_WEB_SEARCH=1 TAVILY_API_KEY=... \`
  - `uv run inspect eval examples/inspect/prompt_task.py -T prompt="Curate a list of arXiv papers that Quantinuum published in 2025"`

- Python runner (this example):
  - `INSPECT_ENABLE_WEB_SEARCH=1 TAVILY_API_KEY=... \`
  - `uv run python examples/research/run_local.py "Curate a list of arXiv papers that Quantinuum published in 2025"`
  - With YAML composition: `uv run python examples/research/run_local.py --config examples/research/inspect.yaml "Curate ..."`

Tip: Both pathways load `.env` (repo root and this folder); you can also pass `--env-file <path>` to the runner.

## Quick start
- Install the repo in editable mode: `uv sync` or `pip install -e .`
- Optional: set local provider env (Ollama or LM Studio), or cloud keys.
- Run: `uv run python examples/research/run_local.py "What is Inspect‑AI?"`

### Iterative Agent (no submit)
- A minimal runner that exercises the new Iterative Agent (continuous small steps, time/step bounded):
  - `uv run python examples/research/run_iterative.py "Improve README structure"`
  - With execution tools enabled: `INSPECT_ENABLE_EXEC=1 \`
    `uv run python examples/research/run_iterative.py --time-limit 300 --max-steps 30 "List files and propose edits"`

This iterative runner uses `inspect_agents.build_iterative_agent` and respects standard env-gated tools (exec/search/browser).

#### Inspect task variant (runs via Inspect CLI)
- `uv run inspect eval examples/research/iterative_task.py -T prompt="List files and summarize" -T time_limit=300 -T max_steps=20 -T enable_exec=true`

## Useful flags
- `--enable-web-search`: expose the standard `web_search` tool (works with `TAVILY_API_KEY` or `GOOGLE_CSE_ID` + `GOOGLE_CSE_API_KEY`).
- `--approval dev|ci|prod`: apply approvals presets; dev/prod also enable handoff exclusivity.
- `--env-file <path>`: load a specific `.env` before running.

## Quarantine (handoff input filtering)
- Controlled via env to keep the CLI small:
  - `INSPECT_QUARANTINE_MODE=strict|scoped|off` (default strict)
  - `INSPECT_QUARANTINE_INHERIT=0|1` (default 1)

## Artifacts
- Transcript is written to `.inspect/logs/events.jsonl` after each run.

## Notes
- Previous legacy artifacts were removed. There is no `requirements.txt` here; use the repo install + env variables.

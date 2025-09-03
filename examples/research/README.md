# Research Example (Inspect‑AI Runner)

This example uses the Inspect‑AI runner from this repo — no external agent framework code.

Quick start
- Install the repo in editable mode: `uv sync` or `pip install -e .`
- Optional: set local provider env (Ollama or LM Studio), or cloud keys.
- Run: `uv run python examples/research/run_local.py "What is Inspect‑AI?"`

Useful flags
- `--enable-web-search`: expose the standard `web_search` tool (auto‑works with
  `TAVILY_API_KEY` or `GOOGLE_CSE_ID` + `GOOGLE_CSE_API_KEY`).
- `--approval dev|ci|prod`: apply approvals presets; dev/prod also enable
  handoff exclusivity.
- `--env-file <path>`: load a specific `.env` before running.

Quarantine (handoff input filtering)
- Controlled via env only to keep the CLI small:
  - `INSPECT_QUARANTINE_MODE=strict|scoped|off` (default strict)
  - `INSPECT_QUARANTINE_INHERIT=0|1` (default 1)

Artifacts
- Transcript is written to `.inspect/logs/events.jsonl` after each run.

Notes
- Previous legacy artifacts were removed. There is no
  `requirements.txt` here; use the repo install + env variables.

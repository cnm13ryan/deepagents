# Research Example (Inspect‑AI)

Run the research example using the Inspect‑AI path included in this repo. No DeepAgents/LangGraph or extra example‑only packages are required.

## Quick Run

```bash
# Install the repo (editable install recommended)
uv sync  # or: python3.11 -m venv .venv && source .venv/bin/activate && pip install -e .

# Run the example (local‑first model resolution; no keys required)
uv run python examples/research/run_local.py "What is Inspect‑AI?"
```

Notes
- The runner loads `.env` files (repo root, example folder, or `--env-file`) without overriding existing env vars.
- Model selection defaults to a local provider (Ollama) when nothing is configured; set envs to choose LM‑Studio or remote providers. See Quickstart for details.

## Enable Web Search (optional)

The example uses the Inspect standard `web_search` tool when enabled. Provide one of the providers below or set the CLI flag.

```bash
# Tavily
export TAVILY_API_KEY=...

# Google Programmable Search (CSE)
export GOOGLE_CSE_ID=...
export GOOGLE_CSE_API_KEY=...

# Enable at runtime (also works without setting env ahead of time)
uv run python examples/research/run_local.py --enable-web-search "Research LangGraph vs Inspect"
```

## Approvals & Quarantine (safety)

- Approvals presets: gate sensitive tools and handoffs.

```bash
# Dev: escalate sensitive tools; also enforces handoff exclusivity
uv run python examples/research/run_local.py --approval dev "Delegate research and finish"

# CI: approve all (fast), Prod: terminate on sensitive tools
#   --approval ci | --approval prod
```

- Quarantine (handoff input filtering) via environment:
  - `INSPECT_QUARANTINE_MODE=strict|scoped|off` (default: `strict`)
  - `INSPECT_QUARANTINE_INHERIT=0|1` (default: `1`)

See Reference → Environment Variables for all options.

## YAML Config Variant (optional)

Prefer declarative config? Use the provided YAML to build the same composition:

```bash
# Run using YAML (includes sub‑agents and optional scoped quarantine)
uv run python examples/research/run_local.py --config examples/research/inspect.yaml \
  "Delegate research on Inspect‑AI and summarize"
```

You can still pass `--approval` and `--enable-web-search`; CLI presets and flags
are merged with any approvals/tools from the YAML.

## View Transcripts

Each run writes a JSONL transcript file; printout includes the path.

```bash
# Default viewer (serves ./logs by default)
uv run inspect view
# Or open the directory printed by the example, typically .inspect/logs/
```

More viewer options: CLI → View.

## Troubleshooting

- No model available: start a local provider (e.g., Ollama) or set `INSPECT_EVAL_MODEL` / `DEEPAGENTS_MODEL_PROVIDER` to a reachable backend.
- Web search disabled: set `TAVILY_API_KEY` or `GOOGLE_CSE_ID`+`GOOGLE_CSE_API_KEY`, or use `--enable-web-search`.
- Transcript missing: ensure the process can write to `.inspect/logs` or set `INSPECT_LOG_DIR`.

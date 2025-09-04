# Research Example (Inspect-AI Runner)

This example uses the Inspect-AI runner from this repo – no external agent framework code required.

## Overview: Task vs Runner

There are two complementary entry points in this repository:

1. **Inspect Task** (`examples/inspect/prompt_task.py`): 
   - Exposes an Inspect task via `@task` decorator
   - Execute with: `inspect eval`

2. **Python Runner** (`examples/research/run_local.py`): 
   - Standalone Python script for multi-agent composition
   - Execute directly with Python (not an Inspect task)

> **Note:** Pointing `inspect eval` at the Python runner will fail with "No inspect tasks were found"

## Quick Start

1. **Install the repo in editable mode:**
   ```bash
   uv sync  # or: pip install -e .
   ```

2. **Set environment variables:**
   - Configure local provider (Ollama/LM Studio) or cloud API keys
   - Both repo root and folder `.env` files are loaded
   - Use `--env-file <path>` for custom env files

3. **Run basic example:**
   ```bash
   uv run python examples/research/run_local.py "What is Inspect-AI?"
   ```

## Usage Examples

### Standard Research Task

**Example:** Curate 2025 Quantinuum arXiv papers

Using Inspect task (CLI):
```bash
INSPECT_ENABLE_WEB_SEARCH=1 TAVILY_API_KEY=... \
uv run inspect eval examples/inspect/prompt_task.py \
  -T prompt="Curate a list of arXiv papers that Quantinuum published in 2025"
```

Using Python runner:
```bash
INSPECT_ENABLE_WEB_SEARCH=1 TAVILY_API_KEY=... \
uv run python examples/research/run_local.py \
  "Curate a list of arXiv papers that Quantinuum published in 2025"
```

With YAML composition:
```bash
uv run python examples/research/run_local.py \
  --config examples/research/inspect.yaml "Curate ..."
```

### CI Mode (Single-Handoff)

Enforces single-handoff exclusivity for deterministic CI runs:
```bash
uv run python examples/research/run_local.py \
  --approval ci "Summarize this repository"
```

### Iterative Agent

A minimal runner using `inspect_agents.build_iterative_agent` for continuous small steps:

**Basic usage:**
```bash
uv run python examples/research/run_iterative.py "Improve README structure"
```

**With execution tools:**
```bash
INSPECT_ENABLE_EXEC=1 \
uv run python examples/research/run_iterative.py \
  --time-limit 300 --max-steps 30 "List files and propose edits"
```

**Via Inspect CLI (task variant):**
```bash
uv run inspect eval examples/research/iterative_task.py \
  -T prompt="List files and summarize" \
  -T time_limit=300 \
  -T max_steps=20 \
  -T enable_exec=true
```

## Configuration Options

### Command-Line Flags

- `--provider <name>`: Model provider (e.g., `ollama`, `lm-studio`, `openai`)
- `--model <name>`: Model name (bare or fully qualified like `openai/gpt-4o-mini`)
- `--enable-web-search`: Enable web search tool (requires API keys)
- `--approval dev|ci|prod`: Apply approval presets
- `--env-file <path>`: Load specific environment file
- `--config <path>`: Use YAML configuration file

### Model Selection Examples

```bash
# Local provider with model
uv run python examples/research/run_local.py \
  --provider ollama --model llama3.1 "What is Inspect-AI?"

# Fully qualified model
uv run python examples/research/run_local.py \
  --model openai/gpt-4o-mini "What is Inspect-AI?"
```

### Quarantine Settings

Control handoff input filtering via environment variables:

- `INSPECT_QUARANTINE_MODE`: `strict` (default) | `scoped` | `off`
- `INSPECT_QUARANTINE_INHERIT`: `1` (default) | `0`

## Output

- **Transcript location:** `.inspect/logs/events.jsonl`
- Generated after each run

## Requirements

- Web search requires: `TAVILY_API_KEY` or `GOOGLE_CSE_ID` + `GOOGLE_CSE_API_KEY`
- Environment-gated tools respect standard flags (exec/search/browser)
- CI mode (`--approval ci`) enforces single-handoff exclusivity

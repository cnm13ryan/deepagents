# Iterative Research Task (Inspect‑AI)

This folder contains an Inspect‑AI task, `iterative_task`, that runs a small, iterative “research/coding” agent with optional execution and web tools. The task is defined in `examples/research/iterative_task.py`. For termination, truncation, and configuration details, see the Iterative Agent reference: [Iterative Agent — Termination and Truncation](../../docs/reference/iterative-agent-behavior.md).

## What’s Configured (defaults in this repo)

- Sandbox: `local` — the task runs tools (e.g., `bash`, `python`) inside a per‑sample temp directory via Inspect’s built‑in local sandbox.
- Approvals: preset `ci` — permissive, approves all tools (good for local iteration). Switch to `dev` or `prod` for stricter gates.
- Exec tools: gated by `-T enable_exec=true` (sets `INSPECT_ENABLE_EXEC=1`) so the model can call `bash()`/`python()`.

Source: see the Task at the bottom of `examples/research/iterative_task.py` (imports `approval_preset`, sets `sandbox="local"`, and `approval=approval_preset("ci")`).

## Quick Start

```bash
# 1) Activate your venv (must have inspect-ai>=0.3.129 installed)
source .venv/bin/activate

# 2) Optional: pick a provider/model (defaults try local providers)
#   Ollama example:
#   export DEEPAGENTS_MODEL_PROVIDER=ollama
#   export OLLAMA_MODEL_NAME="qwen3:4b"
#   LM Studio example:
#   export DEEPAGENTS_MODEL_PROVIDER=lm-studio
#   export LM_STUDIO_BASE_URL="http://127.0.0.1:1234/v1"
#   export LM_STUDIO_MODEL_NAME="local-model"

# 3) Create a local log directory to avoid platform path issues
mkdir -p logs

# 4) Run the eval with exec tools enabled (bash/python available in sandbox)
INSPECT_LOG_DIR=./logs \
INSPECT_TRACE_FILE=./logs/trace.log \
inspect eval examples/research/iterative_task.py \
  -T prompt="Curate a list of arXiv papers that Quantinuum published in 2025" \
  -T time_limit=120 -T max_steps=20 -T enable_exec=true
```

### Profiled Run (Tx.Hx.Nx selector)

Use the profile runner to set Tooling (T), Host isolation (H), and Network isolation (N) in one go:

```bash
# T1.H1.N1 = web-only, Docker, allow-listed (configure allowDomains on K8s if using H2)
INSPECT_LOG_DIR=./logs INSPECT_TRACE_FILE=./logs/trace.log \
python examples/research/run_profiled.py \
  --profile T1.H1.N1 \
  --approval dev \
  --time-limit 120 --max-steps 20 \
  "Curate a list of arXiv papers that Quantinuum published in 2025"
```

Examples:
- `--profile T2.H1.N2` → text-only in Docker, offline
- `--profile T0.H2.N1 --enable-browser` → exec + browser in K8s, restricted egress (set `allowDomains` in Helm)

Side note — Finalization
- To always emit a final curated list when the loop stops, add a one‑turn “finalize” step with tools disabled after the loop exits (or instruct the model to output `Final Answer:` and set `stop_on_keywords=["Final Answer:"]`). This guarantees a human‑readable result even if the last exploration step ends on a tool call.

### Examples

The following two runs are useful for quick experiments with tighter time/step budgets:

```bash
# Shorter budget (may truncate exploration)
uv run inspect eval examples/research/iterative_task.py \
  -T prompt="Curate a list of arXiv papers that Quantinuum
  published in 2025" \
  -T time_limit=60 -T max_steps=4 -T enable_exec=true

# Moderate budget (more headroom for tool use and verification)
uv run inspect eval examples/research/iterative_task.py \
  -T prompt="Curate a list of arXiv papers that Quantinuum published in 2025" \
  -T time_limit=120 -T max_steps=8 -T enable_exec=true
```

Side note — Python‑first retrieval
- For structured arXiv queries, prefer `python()` over generic web search: run with `-T enable_exec=true` and leave `INSPECT_ENABLE_WEB_SEARCH` unset (or `0`). In your prompt, ask the agent to: “Use python() to query arXiv (feedparser/requests), filter year==2025, and require authors/affiliations including ‘Quantinuum’.”

Notes
- The model may choose to run Python (e.g., to query arXiv). If a library isn’t present (e.g., `feedparser`), install it:
  - `pip install feedparser`
  - Or allow the agent to run `bash("pip install feedparser")` if your approvals permit it.

Side note — Lightweight validator
- After assembling candidates, add a quick checker step: keep only items with year=2025 and “Quantinuum” in authors/affiliations/comments; deduplicate by arXiv ID; if nothing passes, report “insufficient evidence” instead of guessing.

## Optional: Enable Web Search

Provide a search provider and toggle the tool:

```bash
export INSPECT_ENABLE_WEB_SEARCH=1
# Tavily (recommended):
export TAVILY_API_KEY=...
# or Google CSE:
export GOOGLE_CSE_ID=...; export GOOGLE_CSE_API_KEY=...
```

Side note — When to enable search
- Enable web search only if you lack API‑driven retrieval; for arXiv‑centric tasks, python() with the arXiv API is usually more precise and reproducible than generic search.

## Approvals (Policies)

- Current preset: `ci` (approves all tools).
- Alternatives:
  - `dev`: escalates sensitive tools (e.g., `bash`, `python`, file writes) then rejects by default.
  - `prod`: terminates sensitive tools unless explicitly allowed.

To switch, edit the task and replace `approval_preset("ci")` with `approval_preset("dev")` or `approval_preset("prod")`.

## Sandbox Choices

- Default here is `sandbox="local"` (no Docker required). It runs each tool call in a temp working directory unique to the sample.
- You can switch to Docker if you add a config file and set `sandbox=("docker", "compose.yaml")` (or another supported config), then ensure Docker is available.

## Logging & Traces

- Set `INSPECT_LOG_DIR` to route logs locally (repo `./logs` is a good default).
- Set `INSPECT_TRACE_FILE` to control the trace file location (e.g., `./logs/trace.log`).
- Console UI can be adjusted with `--display` or `INSPECT_DISPLAY`.

## Troubleshooting

- ProcessLookupError: “No sandbox environment has been provided …”
  - This repo’s task sets `sandbox="local"` already. If you still see this, ensure you didn’t override the task’s sandbox with a CLI flag or external config.
- macOS “Operation not permitted” or permission errors under `~/Library/Application Support/inspect_ai/...`:
  - Prefer running with `INSPECT_LOG_DIR=./logs` and `INSPECT_TRACE_FILE=./logs/trace.log` and from a directory your shell can write to.
  - Some Inspect data (e.g., sample buffer DBs) uses the OS user data directory. If your environment restricts writes there, run outside the restricted sandbox or ensure your user can write to `~/Library/Application Support/inspect_ai`.
- Missing Python packages when the model executes code (e.g., `ModuleNotFoundError: feedparser`):
  - Install the package in your venv (`pip install feedparser`) or allow the agent to install via an approved `bash` call.
- Provider auth errors:
  - Remote providers require API keys (e.g., `OPENAI_API_KEY`). For local development, prefer Ollama or LM Studio.

## Advanced Flags

- Time/step limits: `-T time_limit=<sec>` and `-T max_steps=<n>`
- Enable exec tools: `-T enable_exec=true` (maps to `INSPECT_ENABLE_EXEC=1`)
- Enable/disable think tool: `INSPECT_ENABLE_THINK=1` (default on)
- Enable web browser (heavy; requires Playwright): `INSPECT_ENABLE_WEB_BROWSER=1` (use only with a sandbox)

---
Security: Exec and browser tools can run untrusted code. Keep them sandboxed and behind approvals in shared or production environments.

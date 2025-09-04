# Iterative Agent — Termination and Truncation

This document describes how the iterative agent in this repository terminates and how it truncates/prunes state to keep conversations bounded. It also calls out key differences from PaperBench’s `basic_agent_iterative`.

## Overview
- Agent: `build_iterative_agent(...)` in `src/inspect_agents/iterative.py` returns an Inspect‑AI agent that performs small, tool‑driven steps with an ephemeral “continue” nudge each iteration. The nudge is not persisted; assistant replies and tool results are. 〖F:src/inspect_agents/iterative.py†L77-L90〗 〖F:src/inspect_agents/iterative.py†L490-L494〗
- Defaults: safe Files/Todos tools with optional standard tools enabled via env flags (exec, search, browser). 〖F:src/inspect_agents/iterative.py†L45-L56〗 〖F:src/inspect_agents/tools.py†L206-L229〗

## Termination Conditions
- Real‑time limit: When `real_time_limit_sec` (or env `INSPECT_ITERATIVE_TIME_LIMIT`) is set, the loop exits once elapsed time since start meets the limit (optionally subtracting retry wait; see below). 〖F:src/inspect_agents/iterative.py†L315-L323〗
- Max steps: When `max_steps` (or env `INSPECT_ITERATIVE_MAX_STEPS`) is set, the loop exits once `step > max_steps`. 〖F:src/inspect_agents/iterative.py†L324-L326〗
- Stop on keywords: If `stop_on_keywords` is provided and the latest assistant message contains any keyword (case‑insensitive), the loop exits early. 〖F:src/inspect_agents/iterative.py†L625-L631〗
- External Inspect limits: The runner can supply Inspect limits (time/message/token) via `run_agent(..., limits=[...])`. When limits are provided, Inspect’s engine enforces them and returns `(state, err)`; the run helper can raise or propagate the error. 〖F:src/inspect_agents/run.py†L21-L35〗 〖F:src/inspect_agents/run.py†L37-L57〗

Per‑call timeouts: To avoid overruns, each model `generate(...)` call receives a timeout equal to remaining time; tool execution is likewise wrapped with an `asyncio.timeout` based on the remaining budget. 〖F:src/inspect_agents/iterative.py†L495-L503〗 〖F:src/inspect_agents/iterative.py†L578-L600〗

## Truncation and Pruning
- List‑length pruning each step: `_prune_history(...)` keeps the first system + first user messages, and then a tail window of recent turns (assistant/user/tool) sized by either `max_messages` (when set) or `2 * max_turns`. It also drops orphan tool messages whose parent assistant call is not present. 〖F:src/inspect_agents/iterative.py†L239-L295〗
- Threshold‑based global prune: When the message count exceeds `prune_after_messages` (default 120, overrideable via `INSPECT_PRUNE_AFTER_MESSAGES`), the agent applies `_conversation.prune_messages(messages, keep_last=prune_keep_last)` and logs (when debug is enabled). 〖F:src/inspect_agents/iterative.py†L450-L487〗 〖F:src/inspect_agents/_conversation.py†L69-L105〗
- Context overflow handling: If a provider signals length overflow (e.g., `IndexError` or `stop_reason == "model_length"`), the agent appends a short hint — “Context too long; please summarize recent steps and continue.” — then immediately prunes, and continues. 〖F:src/inspect_agents/iterative.py†L528-L571〗 〖F:src/inspect_agents/_conversation.py†L30-L48〗
- Ephemeral nudges are not persisted: the per‑step continue message is added to a copy of history for that turn only. 〖F:src/inspect_agents/iterative.py†L490-L494〗

### Tool‑Output Truncation
- Effective global limit: The env var `INSPECT_MAX_TOOL_OUTPUT` (bytes) can set `active_generate_config.max_tool_output` once on first tool invocation via the tools layer; otherwise a 16 KiB default applies. 〖F:src/inspect_agents/tools.py†L80-L115〗 〖F:src/inspect_agents/tools.py†L106-L115〗
- Note: This is applied by our tool wrappers (Files/Todos). Standard tools from Inspect (e.g., `bash`, `python`) have their own behavior; if you want a guaranteed global cap for them too, set `INSPECT_MAX_TOOL_OUTPUT` in the environment before any tool calls or configure the active GenerateConfig in your runner.

## Differences vs PaperBench `basic_agent_iterative`
- Retry‑time accounting: PaperBench always subtracts provider backoff/retry time from the time budget. Our implementation does this when `INSPECT_PRODUCTIVE_TIME=1`, and uses wall‑clock only when the flag is unset. 〖F:external/paperbench/paperbench/agents/aisi-basic-agent/_basic_agent_iterative.py†L209-L216〗 〖F:src/inspect_agents/iterative.py†L300-L323〗
- Per‑message token truncation: PaperBench can trim individual oversized messages (~190k‑token cap) when providers signal this; our implementation prunes by message count only (first system + first user + tail window). 〖F:external/paperbench/paperbench/agents/aisi-basic-agent/utils.py†L203-L211〗 〖F:src/inspect_agents/_conversation.py†L69-L105〗
- Provider‑specific safeguards: PaperBench proactively prunes near 900 messages for Claude Sonnet; our implementation uses generic thresholds (configurable via env), not provider‑specific heuristics. 〖F:external/paperbench/paperbench/agents/aisi-basic-agent/_basic_agent_iterative.py†L197-L199〗 〖F:src/inspect_agents/iterative.py†L290-L307〗
- Tool output limit wiring: PaperBench passes `max_tool_output` directly to tool execution; our approach relies on the active GenerateConfig (settable via env) and our wrappers. 〖F:external/paperbench/paperbench/agents/aisi-basic-agent/_basic_agent_iterative.py†L279-L282〗 〖F:src/inspect_agents/tools.py†L80-L115〗

- `INSPECT_ITERATIVE_TIME_LIMIT` — seconds; wall‑clock cap when `real_time_limit_sec` is not explicitly set. 〖F:src/inspect_agents/iterative_config.py†L24-L50〗
- `INSPECT_ITERATIVE_MAX_STEPS` — integer; step cap when `max_steps` is not explicitly set. 〖F:src/inspect_agents/iterative_config.py†L24-L50〗
- `INSPECT_PRUNE_AFTER_MESSAGES` — integer; threshold for global prune (non‑positive disables). 〖F:src/inspect_agents/iterative_config.py†L53-L93〗
- `INSPECT_PRUNE_KEEP_LAST` — integer; how many messages to keep in each global prune. 〖F:src/inspect_agents/iterative_config.py†L53-L93〗
- `INSPECT_PRUNE_DEBUG` — truthy; adds info logs for prune operations. 〖F:src/inspect_agents/iterative.py†L263-L268〗
- `INSPECT_MAX_TOOL_OUTPUT` — bytes; sets global tool output cap via active GenerateConfig (16 KiB default). 〖F:src/inspect_agents/tools.py†L80-L115〗
- Standard tool toggles: `INSPECT_ENABLE_EXEC`, `INSPECT_ENABLE_WEB_SEARCH`, `INSPECT_ENABLE_WEB_BROWSER`, `INSPECT_ENABLE_TEXT_EDITOR_TOOL`. 〖F:src/inspect_agents/tools.py†L206-L229〗 〖F:src/inspect_agents/tools.py†L300-L340〗

## Testing Hooks
- `clock: Callable[[], float]` — optional injection for deterministic timing in tests (defaults to `time.time`). Used for elapsed/remaining calculations and progress pings. 〖F:src/inspect_agents/iterative.py†L100-L103〗 〖F:src/inspect_agents/iterative.py†L315-L323〗 〖F:src/inspect_agents/iterative.py†L420-L441〗
- `timeout_factory: Callable[[int], AsyncContextManager]` — optional injection replacing `asyncio.timeout` during tool execution (defaults preserved). 〖F:src/inspect_agents/iterative.py†L100-L103〗 〖F:src/inspect_agents/iterative.py†L597-L600〗

## CLI Usage (configure the Iterative Agent)

You can configure time/step limits and optional tools either via example CLIs in this repo or through the Inspect CLI task parameters.

### Python runner (`examples/research/run_iterative.py`)

Flags:
- `--time-limit <sec>`: wall‑clock budget forwarded to `real_time_limit_sec`. 〖F:examples/research/run_iterative.py†L76〗
- `--max-steps <n>`: hard cap on loop steps. 〖F:examples/research/run_iterative.py†L77〗
- `--enable-exec`: set `INSPECT_ENABLE_EXEC=1` so `bash()`/`python()` are available. 〖F:examples/research/run_iterative.py†L78-L93〗
- `--provider`/`--model`: choose model provider and model id (overrides env). 〖F:examples/research/run_iterative.py†L79-L84〗

Example:
```bash
uv run python examples/research/run_iterative.py \
  --time-limit 300 --max-steps 20 \
  "Create docs/OUTLINE.md and add 3 sections"
```

### Profiled runner (`examples/research/run_profiled.py`)

Use a single profile (Tx.Hx.Nx) and fine‑tune with flags:
- `--profile T{0|1|2}.H{0|1|2|3}.N{0|1|2}`: tooling/host/network profile. 〖F:examples/research/run_profiled.py†L69-L77〗
- `--time-limit <sec>` / `--max-steps <n>`: pass through to the agent. 〖F:examples/research/run_profiled.py†L76-L77〗 〖F:examples/research/run_profiled.py†L111-L114〗
- `--enable-browser`, `--enable-web-search`: opt‑in heavy tools as needed. 〖F:examples/research/run_profiled.py†L78-L84〗 〖F:examples/research/run_profiled.py†L96-L103〗
- `--approval {ci,dev,prod}`: select an approvals preset. 〖F:examples/research/run_profiled.py†L75〗 〖F:examples/research/run_profiled.py†L116-L123〗

Example:
```bash
python examples/research/run_profiled.py \
  --profile T1.H1.N1 --approval dev \
  --time-limit 120 --max-steps 20 \
  "Curate a list of arXiv papers that Quantinuum published in 2025"
```

### Inspect CLI task (`examples/research/iterative_task.py`)

Set task parameters with `-T key=value`:
- `-T time_limit=<sec>` → `real_time_limit_sec`. 〖F:examples/research/iterative_task.py†L31-L33〗 〖F:examples/research/iterative_task.py†L46-L48〗
- `-T max_steps=<n>` → `max_steps`. 〖F:examples/research/iterative_task.py†L31-L33〗 〖F:examples/research/iterative_task.py†L46-L48〗
- `-T enable_exec=true` → sets `INSPECT_ENABLE_EXEC=1` before building tools. 〖F:examples/research/iterative_task.py†L37-L38〗

Example:
```bash
uv run inspect eval examples/research/iterative_task.py \
  -T prompt="List files and propose a small refactor plan" \
  -T time_limit=300 -T max_steps=30 -T enable_exec=true
```

## Example
```python
from inspect_agents.agents import build_iterative_agent
from inspect_agents.run import run_agent

agent = build_iterative_agent(
    prompt="Iteratively improve README and examples.",
    real_time_limit_sec=900,  # 15 minutes
    max_steps=50,
    stop_on_keywords=["all done", "complete"],
)

state = await run_agent(agent, "Start by listing files and reading README.md")
print(state.output.choices[0].message.text)
```

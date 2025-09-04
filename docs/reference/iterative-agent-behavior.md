# Iterative Agent — Termination and Truncation

This document describes how the iterative agent in this repository terminates and how it truncates/prunes state to keep conversations bounded. It also calls out key differences from PaperBench’s `basic_agent_iterative`.

## Overview
- Agent: `build_iterative_agent(...)` in `src/inspect_agents/iterative.py` returns an Inspect‑AI agent that performs small, tool‑driven steps with an ephemeral “continue” nudge each iteration. The nudge is not persisted; assistant replies and tool results are. 〖F:src/inspect_agents/iterative.py†L76-L90〗 〖F:src/inspect_agents/iterative.py†L318-L325〗
- Defaults: safe Files/Todos tools with optional standard tools enabled via env flags (exec, search, browser). 〖F:src/inspect_agents/iterative.py†L62-L74〗 〖F:src/inspect_agents/tools.py†L206-L229〗

## Termination Conditions
- Real‑time limit: When `real_time_limit_sec` (or env `INSPECT_ITERATIVE_TIME_LIMIT`) is set, the loop exits once elapsed wall‑clock time since start meets the limit. 〖F:src/inspect_agents/iterative.py†L129-L138〗 〖F:src/inspect_agents/iterative.py†L271-L279〗
- Max steps: When `max_steps` (or env `INSPECT_ITERATIVE_MAX_STEPS`) is set, the loop exits once `step > max_steps`. 〖F:src/inspect_agents/iterative.py†L279-L287〗
- Stop on keywords: If `stop_on_keywords` is provided and the latest assistant message contains any keyword (case‑insensitive), the loop exits early. 〖F:src/inspect_agents/iterative.py†L398-L407〗
- External Inspect limits: The runner can supply Inspect limits (time/message/token) via `run_agent(..., limits=[...])`. When limits are provided, Inspect’s engine enforces them and returns `(state, err)`; the run helper can raise or propagate the error. 〖F:src/inspect_agents/run.py†L21-L35〗 〖F:src/inspect_agents/run.py†L37-L57〗

Per‑call timeouts: To avoid overruns, each model `generate(...)` call receives a timeout equal to remaining wall time; tool execution is likewise wrapped with an `asyncio.timeout` based on the remaining budget. 〖F:src/inspect_agents/iterative.py†L327-L336〗 〖F:src/inspect_agents/iterative.py†L368-L383〗

## Truncation and Pruning
- List‑length pruning each step: `_prune_history(...)` keeps the first system + first user messages, and then a tail window of recent turns (assistant/user/tool) sized by either `max_messages` (when set) or `2 * max_turns`. It also drops orphan tool messages whose parent assistant call is not present. 〖F:src/inspect_agents/iterative.py†L308-L360〗
- Threshold‑based global prune: When the message count exceeds `prune_after_messages` (default 120, overrideable via `INSPECT_PRUNE_AFTER_MESSAGES`), the agent applies `_conversation.prune_messages(messages, keep_last=prune_keep_last)` and logs (when debug is enabled). 〖F:src/inspect_agents/iterative.py†L290-L307〗 〖F:src/inspect_agents/_conversation.py†L69-L105〗
- Context overflow handling: If a provider signals length overflow (e.g., `IndexError` or `stop_reason == "model_length"`), the agent appends a short hint — “Context too long; please summarize recent steps and continue.” — then immediately prunes, and continues. 〖F:src/inspect_agents/iterative.py†L337-L367〗 〖F:src/inspect_agents/_conversation.py†L30-L48〗
- Ephemeral nudges are not persisted: the per‑step continue message is added to a copy of history for that turn only. 〖F:src/inspect_agents/iterative.py†L318-L325〗

### Tool‑Output Truncation
- Effective global limit: The env var `INSPECT_MAX_TOOL_OUTPUT` (bytes) can set `active_generate_config.max_tool_output` once on first tool invocation via the tools layer; otherwise a 16 KiB default applies. 〖F:src/inspect_agents/tools.py†L80-L115〗 〖F:src/inspect_agents/tools.py†L106-L115〗
- Note: This is applied by our tool wrappers (Files/Todos). Standard tools from Inspect (e.g., `bash`, `python`) have their own behavior; if you want a guaranteed global cap for them too, set `INSPECT_MAX_TOOL_OUTPUT` in the environment before any tool calls or configure the active GenerateConfig in your runner.

## Differences vs PaperBench `basic_agent_iterative`
- Retry‑time accounting: PaperBench subtracts provider backoff/retry time (`total_retry_time`) from the time budget; our implementation uses wall‑clock elapsed only. 〖F:external/paperbench/paperbench/agents/aisi-basic-agent/_basic_agent_iterative.py†L209-L216〗 〖F:src/inspect_agents/iterative.py†L271-L279〗
- Per‑message token truncation: PaperBench can trim individual oversized messages (~190k‑token cap) when providers signal this; our implementation prunes by message count only (first system + first user + tail window). 〖F:external/paperbench/paperbench/agents/aisi-basic-agent/utils.py†L203-L211〗 〖F:src/inspect_agents/_conversation.py†L69-L105〗
- Provider‑specific safeguards: PaperBench proactively prunes near 900 messages for Claude Sonnet; our implementation uses generic thresholds (configurable via env), not provider‑specific heuristics. 〖F:external/paperbench/paperbench/agents/aisi-basic-agent/_basic_agent_iterative.py†L197-L199〗 〖F:src/inspect_agents/iterative.py†L290-L307〗
- Tool output limit wiring: PaperBench passes `max_tool_output` directly to tool execution; our approach relies on the active GenerateConfig (settable via env) and our wrappers. 〖F:external/paperbench/paperbench/agents/aisi-basic-agent/_basic_agent_iterative.py†L279-L282〗 〖F:src/inspect_agents/tools.py†L80-L115〗

## Configuration Reference
- `INSPECT_ITERATIVE_TIME_LIMIT` — seconds; wall‑clock cap when `real_time_limit_sec` is not explicitly set. 〖F:src/inspect_agents/iterative.py†L129-L138〗
- `INSPECT_ITERATIVE_MAX_STEPS` — integer; step cap when `max_steps` is not explicitly set. 〖F:src/inspect_agents/iterative.py†L279-L287〗
- `INSPECT_PRUNE_AFTER_MESSAGES` — integer; threshold for global prune (non‑positive disables). 〖F:src/inspect_agents/iterative.py†L156-L167〗
- `INSPECT_PRUNE_KEEP_LAST` — integer; how many messages to keep in each global prune. 〖F:src/inspect_agents/iterative.py†L168-L176〗
- `INSPECT_PRUNE_DEBUG` — truthy; adds info logs for prune operations. 〖F:src/inspect_agents/iterative.py†L180-L188〗
- `INSPECT_MAX_TOOL_OUTPUT` — bytes; sets global tool output cap via active GenerateConfig (16 KiB default). 〖F:src/inspect_agents/tools.py†L80-L115〗
- Standard tool toggles: `INSPECT_ENABLE_EXEC`, `INSPECT_ENABLE_WEB_SEARCH`, `INSPECT_ENABLE_WEB_BROWSER`, `INSPECT_ENABLE_TEXT_EDITOR_TOOL`. 〖F:src/inspect_agents/tools.py†L206-L229〗 〖F:src/inspect_agents/tools.py†L300-L340〗

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


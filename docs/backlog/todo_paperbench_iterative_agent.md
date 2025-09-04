# Deepagents Iterative Agent (neutral ephemeral re‑prompt loop)

This document explains the implemented Iterative Agent, modeled after PaperBench’s “iterative” loop but adapted to deepagents’ Inspect‑AI–native stack. It is suitable for long‑lived, exploratory automation where you want steady progress without a submit/scoring path.

Overview
- Goal: Incremental, tool‑driven progress with an ephemeral “continue” nudge each step (the nudge is not persisted in history). The model’s assistant reply and any tool results are persisted.
- Termination: Real‑time limit and/or max step count (no submit tool). External limits via Inspect’s limits API are also supported.
- Defaults: Safe tool set (Files/Todos built‑ins). Exec/search/browser are opt‑in via env flags.

API
- Builder: `build_iterative_agent(...)` in `src/inspect_agents/iterative.py` 〖F:src/inspect_agents/iterative.py†L104-L122〗
  - `prompt: str | None` — optional system message (neutral default provided). 〖F:src/inspect_agents/iterative.py†L76-L90〗
  - `tools: Sequence[object] | None` — optional extra tools; defaults to Files tools plus env‑enabled standard tools. 〖F:src/inspect_agents/iterative.py†L62-L74〗
  - `model: Any | None` — optional Inspect model; falls back to active model.
  - `real_time_limit_sec: int | None` — wall‑clock time budget.
  - `max_steps: int | None` — cap on loop iterations.
  - `continue_message: str | None` — custom ephemeral nudge.

Loop Semantics
- Each iteration builds a temporary conversation = history + ephemeral continue user message; calls `model.generate(...)`; appends only the assistant message to history; then executes any tool calls with a timeout based on remaining time. 〖F:src/inspect_agents/iterative.py†L130-L168〗
- A small progress ping is persisted every 5 steps: `Info: HH:MM:SS elapsed`. 〖F:src/inspect_agents/iterative.py†L122-L133〗
- If there are no tool calls, the agent appends a gentle “Please continue.” nudge to keep momentum. 〖F:src/inspect_agents/iterative.py†L162-L168〗

Default Tools and Env Flags
- Files/Todos store‑backed tools are always available; `standard_tools()` appends optional tools based on environment flags. 〖F:src/inspect_agents/tools.py†L206-L229〗
- To enable exec (bash/python): `INSPECT_ENABLE_EXEC=1`. To enable web search/browser, set the corresponding flags and provider keys per `docs/tools/*` guides.

Usage Example
```python
from inspect_agents.agents import build_iterative_agent
from inspect_agents.run import run_agent

agent = build_iterative_agent(
    prompt="Iteratively improve the repo’s README and examples.",
    real_time_limit_sec=900,  # 15 minutes
    max_steps=50,
)

state = await run_agent(agent, "Start by listing files and reading README.md")
print(state.output.choices[0].message.text)
```

Notes
- Ephemeral hints aren’t stored: they never bloat the visible conversation. 〖F:src/inspect_agents/iterative.py†L130-L138〗
- Per‑call timeouts derive from remaining budget to avoid overruns. 〖F:src/inspect_agents/iterative.py†L138-L149〗
- You can pass your own tools; they’ll be combined with the safe defaults.

Related Internals
- Exported via `from inspect_agents.agents import build_iterative_agent`. 〖F:src/inspect_agents/agents.py†L141-L152〗
- Run helper: `src/inspect_agents/run.py` integrates with Inspect’s agent runner. 〖F:src/inspect_agents/run.py†L6-L18〗

# Supervisor Limits & Observability — Practical Guide

This guide explains how DeepAgents (Inspect‑native) applies execution limits for safety, cost control, and determinism, and how to observe/diagnose limit events.

What you get
- Supervisor: submit‑terminated ReAct loop with `attempts` control.
- Runner budgets: apply global limits at the call site.
- Sub‑agent guardrails: per‑handoff limits for targeted control.
- Structured logs when nearing/exceeding limits; no user‑visible footers by default.

Scope & Principles
- Keep the top‑level supervisor simple (no local `limits` param); rely on the runner for global budgets.  
- Constrain sub‑agents at the handoff boundary where most risk/cost concentrates.  
- Prefer deterministic limits in tests (message/tool‑call) and generous slack for time/token.

Where limits live
- Supervisor: `build_supervisor(prompt, tools, attempts=..., model=..., truncation=...)` — no `limits` here.  
- Sub‑agents: `handoff(agent, ..., limits=[...])` to cap message/tool activity per handoff.  
- Runner: `run_agent(agent, input, limits=[...])` for wall‑clock, tokens, or global message caps.

Recommended Defaults
- attempts: 1 (submit‑terminated); raise per workload if needed.  
- runner time limit: 60–120s (environment dependent).  
- token limit: off by default (enable only when budgeting is critical; add buffer).  
- handoff message/tool‑call limits: small, deterministic caps (e.g., 8–24 messages; 8–16 tool calls).

Observability
- Emit `limit_nearing` (≥80%) and `limit_exceeded` events with fields:  
  `agent_name`, `scope` (runner|handoff), `limit_kind` (message|tool|token|time), `threshold`, `used`, `exceeded_by` (if known).  
- Keep completions clean: no footer by default; enable via a setting if required.

Examples
```python
# Runner‑level wall‑clock (global)
from inspect_ai.util import time_limit
result = await run_agent(agent, "start", limits=[time_limit(90)])

# Handoff‑level message cap (targeted)
from inspect_ai.limits import message_limit
handoff_agent = handoff(sub_agent, description="researcher", limits=[message_limit(12)])
```

Propagating Limit Errors
```python
from inspect_ai.util import time_limit, LimitExceededError

# Return the error tuple for branching without parsing logs
state, err = await run_agent(
    agent,
    "start",
    limits=[time_limit(0)],
    return_limit_error=True,
)
if err is not None:
    print(f"Limit hit: {type(err).__name__}")

# Or raise on limit exceed to use try/except control flow
try:
    await run_agent(agent, "start", limits=[time_limit(0)], raise_on_limit=True)
except LimitExceededError:
    print("Limit exceeded — handle or retry")
```

Testing Tips
- Use message/tool‑call limits to assert early exit deterministically.  
- For time/token, add slack and assert the reason is surfaced.  
- Verify logs contain `limit_exceeded` with expected scope/kind.

Design Pointers
- Supervisor built via `react(..., submit=True)` with `attempts` plumbed.  
- Sub‑agents wrap `handoff(..., limits=[...])`.  
- Runner forwards `limits` via `agent_run(..., limits=...)`.

See also
- Decision D0003: rationale and rollout details (`docs/adr/0003-supervisor-limits-and-observability.md`).

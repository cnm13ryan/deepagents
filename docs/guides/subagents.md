# Sub‑agent Recipes

This page provides practical recipes for configuring and using sub‑agents with Inspect, covering both `handoff` (control‑flow delegation) and `tool` (single‑shot) modes, quarantine filters, nested handoffs, and execution limits.

## Choose the Right Mode

- Handoff: delegate control to a sub‑agent that can plan, call tools, and iterate until it finishes (mirrors legacy `task`). Produces a tool named `transfer_to_<name>`.
- Tool: call the sub‑agent once like a function (deterministic, stateless helpers).

See README for a quick overview; this page dives deeper.

## Recipe: Researcher (handoff) with Quarantine + Limits

Programmatic construction (recommended when applying limits):

```python
from inspect_ai.agent import react
from inspect_ai.util import time_limit, token_limit, message_limit
from inspect_agents.agents import build_subagents, build_supervisor

# Base built-ins come from build_supervisor; pass any extra tools you need
base_tools = []

sub_cfgs = [
    {
        "name": "researcher",
        "description": "Focused web researcher that plans and cites sources",
        "prompt": "Research the user’s query. Plan, browse, then draft findings.",
        "mode": "handoff",
        "tools": ["web_search", "write_todos", "read_file", "write_file"],
        # Quarantine filters come from defaults; override via env or explicit filters
        # Limits: apply Inspect limit objects per handoff
        "limits": [
            time_limit(60),      # stop after 60s of wall time inside the handoff
            message_limit(8),    # stop after 8 assistant/user turns in the handoff
            token_limit(6000),   # stop after ~6000 tokens consumed in the handoff
        ],
    }
]

sub_tools = build_subagents(sub_cfgs, base_tools)

agent = build_supervisor(
    prompt="You are a helpful supervisor.",
    tools=sub_tools,
    attempts=1,
)
```

YAML configuration (illustrative spec):

```yaml
supervisor:
  prompt: |
    You are a helpful supervisor. Use sub‑agents when appropriate.

subagents:
  - name: researcher
    description: Focused web researcher that plans and cites sources
    prompt: |
      Research the user’s query. Plan, browse, then draft findings.
    mode: handoff
    tools: [web_search, write_todos, read_file, write_file]
    # Limits (spec form). Bind via Python: see programmatic example above.
    limits:
      - type: time
        seconds: 60
      - type: messages
        max: 8
      - type: tokens
        max: 6000
```

Notes
- Limits are Inspect `Limit` objects; construct them programmatically (time/message/token). The YAML “spec” above is a documentation aid; bind them in code until a parser maps specs → limit objects.
- Quarantine defaults: strict filtering and optional scoped JSON state summary are provided via `inspect_agents.filters`. Use env overrides to tweak behavior.

## Recipe: Summarizer (as tool)

```yaml
subagents:
  - name: summarizer
    description: Five concise bullets from provided text
    prompt: |
      Summarize the given content in exactly five bullets.
    mode: tool
    tools: []
```

Behavior
- Called once; returns output directly to the caller.
- Quarantine filters generally don’t apply (single‑shot call).

## Nested Handoffs

Sub‑agents using `handoff` can delegate to other sub‑agents. Defaults ensure the input filter selection cascades within a subtask context.

Example (programmatic sketch):

```python
from inspect_ai.util import time_limit
from inspect_agents.agents import build_subagents

sub_cfgs = [
    {"name": "researcher", "description": "...", "prompt": "...", "mode": "handoff", "limits": [time_limit(45)]},
    {"name": "writer", "description": "...", "prompt": "...", "mode": "handoff"},
]
tools = build_subagents(sub_cfgs, base_tools=[])
# researcher can call transfer_to_writer if both tools are included in its tool list
```

## Quarantine Controls (Env)

- `INSPECT_QUARANTINE_MODE`: `strict` (default) | `scoped` | `off`
- `INSPECT_QUARANTINE_MODE__<normalized_name>`: per‑agent override (name lower‑cased, non‑alphanumeric → `_`).
- `INSPECT_QUARANTINE_INHERIT`: cascade parent filter within a subtask (default: true).
- Scoped summary size: `INSPECT_SCOPED_MAX_BYTES`, `INSPECT_SCOPED_MAX_TODOS`, `INSPECT_SCOPED_MAX_FILES`.

## Migration Tips

- Legacy `task(researcher)` ≈ call `transfer_to_researcher` (handoff).
- Start with `handoff` to preserve behavior, then convert narrow helpers to `tool` for efficiency.


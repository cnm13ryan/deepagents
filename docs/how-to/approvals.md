# Approvals & Policies — How‑To

This guide shows how to add review gates for tool calls using Inspect’s approval system as wired by this repo. You’ll learn how to initialize approvals, use presets, declare custom policies, and review decisions in logs.

## TL;DR
- Pass a list of approval policies to your run (or initialize them once) to gate sensitive tools.
- Use presets for `ci`, `dev`, or `prod` behavior; customize with allow/modify/reject/terminate.
- Review decisions in Inspect logs and traces; tool events include redacted arguments and durations.

## Initialization
Approvals are applied at runtime via Inspect’s tool approval mechanism. This repo wires them in two common paths:

- Provide `approval=` to the async runner:
```python
result = await run_agent(agent, "start", approval=policies)
```

- Or initialize once for the process:
```python
from inspect_agents.approval import activate_approval_policies
activate_approval_policies(policies)
```

Both methods call Inspect’s approval init under the hood. If the approval module is stubbed (e.g., in tests), initialization is a safe no‑op.

## Presets (ci | dev | prod)
Use built‑in presets to start quickly:

```python
from inspect_agents.approval import approval_preset

policies = approval_preset("dev")   # or "ci", "prod"
```

Preset behavior:
- `ci`: approve all tools (no‑op gate). 
- `dev`: approve most; escalate sensitive tools to a second policy that rejects them (good for local safety).
- `prod`: terminate sensitive tools with a redacted explanation.

Sensitive tools (matched by name):
- `write_file`, `text_editor`, `bash`, `python`, and any `web_browser_*` tool.

Tip: Combine presets with targeted custom rules (below) for fine control.

## Custom Policies (declarative)
You can express approvals using a compact mapping and convert it to Inspect policies:

```python
from inspect_agents.approval import approval_from_interrupt_config

cfg = {
    "ls": True,  # approve with defaults
    "write_file": {"decision": "modify", "modify_args": {"file_path": "README.md"}},
    "bash": {"decision": "reject", "explanation": "No shell in this environment"},
    "web_browser_*": {"decision": "terminate", "explanation": "Not allowed"},
}

policies = approval_from_interrupt_config(cfg)
```

Rules:
- Keys are exact tool names or glob patterns.
- Values: `True` (approve with defaults) or an object with fields:
  - `decision`: `approve | modify | reject | terminate`.
  - `modify_args` / `modified_args`: dict of new tool arguments when `decision==modify`.
  - `modify_function` / `modified_function`: optional new tool name when modifying.
  - `allow_accept` (default true), `allow_edit` (default true).
- `allow_ignore=True` is not supported and raises a validation error.

## Review Signals (Logs & Traces)
Approvals integrate with Inspect’s transcript and tracing:
- Inspect logs: after a run, list logs and dump JSON to review approval outcomes and tool events:
  ```bash
  uv run inspect log list --log-dir logs
  uv run inspect log dump logs/<run>.eval | jq
  ```
- Live traces: list/dump traces to correlate model/tool retries and decisions:
  ```bash
  uv run inspect trace list
  uv run inspect trace dump logs/inspect_ai/trace.log | jq
  ```

Tool lifecycle events emitted by this repo include:
- `tool`: name, `phase`: `start|end|error`, optional `duration_ms`.
- Redacted/truncated `args` (see Redaction below).

## Redaction & Truncation
- Arguments are redacted for keys such as `api_key`, `authorization`, `token`, `password`, `file_text`, `content`.
- Truncation: long string fields are truncated (default 200 characters) in log lines; configure with `INSPECT_TOOL_OBS_TRUNCATE`.

## Examples
### Dev preset with explicit activation
```python
from inspect_agents.approval import approval_preset, activate_approval_policies
activate_approval_policies(approval_preset("dev"))
```

### Run with policies passed inline
```python
from inspect_agents.approval import approval_preset
policies = approval_preset("prod")
result = await run_agent(agent, "start", approval=policies)
```

## Troubleshooting
- “Nothing happened” on a tool call you expected: In `dev` preset, sensitive tools escalate then get rejected. Use `ci` preset to confirm flow, then add a precise allow rule.
- Need to tweak one tool only in production: Start from `prod` preset and add a single allow/modify rule for that tool.
- Logs look empty: ensure you set `--log-dir logs` (Inspect CLI) or `INSPECT_LOG_DIR=.inspect/logs` when using the Python path, then inspect the generated `.eval` files.

## Notes & Best Practices
- Keep `dev` safe by default; approve only the minimal set of tools you need while iterating.
- Prefer `modify` over blanket `approve` for risky tools: inject safe arguments (paths, timeouts) in the policy.
- Pair approvals with sandboxed FS and disabled browser/exec unless explicitly required.


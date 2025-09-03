---
title: "<tool_name> Reference"
status: draft
kind: builtin|standard
mode: stateless|stateful
owner: docs
---

# <tool_name>

## Overview
- What it does: <one-sentence purpose>.
- When to use it: <situations/alternatives>.
- Classification: <stateless|stateful>. See ../guides/stateless-vs-stateful-tools-harmonized.md.

## Parameters
- name: <type> — <description>. Default: <value>.
- …

## Result Schema
- field: <type> — <description>.
- errors: <list or enum>.

## Timeouts & Limits
- Execution timeout: <seconds>.
- Size limits: <bytes/lines>; truncation behavior: <behavior>.
- Sandbox/FS notes: <store|sandbox behaviors>.

## Examples
### CLI
```bash
# Example invocation
inspect eval examples/inspect/prompt_task.py -T prompt="..." \
  -T tool_call='{"tool": "<tool_name>", "args": {...}}'
```

### Agent prompt snippet
```
Use the <tool_name> tool with args {...} to <goal>.
```

### Failure case
> Symptom: <error>
> Fix: <remediation>

## Safety & Best Practices
- Avoid: <pitfall>.
- Prefer: <pattern>.
- Redaction/PII: <notes>.

## Troubleshooting
- Message: <common error> — Resolution: <action>.
- …

## Source of Truth
- Code: src/inspect_agents/<file>.py
- Related guides: ../guides/tool-umbrellas.md


---
title: "python Reference"
status: draft
kind: standard
mode: stateless
owner: docs
---

# python

## Overview
- Executes a one-shot Python script in a sandboxed process.
- Classification: stateless.

## Parameters
- code: string — Python source to run. Required.
- timeout: int — Optional seconds cap.

## Result Schema
- stdout: string
- stderr: string
- exit_code: int

## Timeouts & Limits
- Defaults are defined by Inspect’s standard `python` tool; this repo does not override them. See Inspect documentation for authoritative limits and output policies.

## Enablement
- Disabled by default. Set `INSPECT_ENABLE_EXEC=1` to enable `python` (and `bash`).

## Examples
```
Compute a quick result and print JSON to stdout.
```

## Safety & Best Practices
- No network or filesystem unless explicitly allowed by environment.

## Troubleshooting
- Import errors — Ensure dependencies are available in the sandbox.

## Source of Truth
- Code: src/inspect_agents/tools.py

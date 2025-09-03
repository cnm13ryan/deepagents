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
- Execution timeout: TBD. Output truncation caps: TBD.

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


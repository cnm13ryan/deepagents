---
title: "bash Reference"
status: draft
kind: standard
mode: stateless
owner: docs
---

# bash

## Overview
- Executes a single bash command in a sandboxed process.
- Classification: stateless.

## Parameters
- command: string — Shell command. Required.
- timeout: int — Optional seconds cap.

## Result Schema
- stdout: string
- stderr: string
- exit_code: int

## Timeouts & Limits
- Execution timeout: TBD. Output truncation caps: TBD.

## Examples
```
Run a simple build command and capture logs.
```

## Safety & Best Practices
- Avoid destructive commands; prefer read-only operations.

## Troubleshooting
- Non-zero exit — Inspect stderr and exit_code.

## Source of Truth
- Code: src/inspect_agents/tools.py


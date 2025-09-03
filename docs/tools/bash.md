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
- Defaults are defined by Inspect’s standard `bash` tool; this repo does not override them. See Inspect documentation for authoritative limits and output policies.

## Enablement
- Disabled by default. Set `INSPECT_ENABLE_EXEC=1` to enable `bash` (and `python`).

## Notes
- This repo does not alter sandbox constraints for `bash`; follow upstream security guidelines.

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

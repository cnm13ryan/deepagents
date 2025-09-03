---
title: "think Reference"
status: draft
kind: standard
mode: stateless
owner: docs
---

# think

## Overview
- Appends a thought/log note with no side effects.
- Use for chain-of-thought markers or to explain the next action (kept concise).
- Classification: stateless.

## Parameters
- message: string — The note to record. Required.

## Result Schema
- ok: bool
- echo: string

## Timeouts & Limits
- Execution timeout: TBD. Max length: TBD.

## Examples
```
Record intent before taking a risky action.
```

## Safety & Best Practices
- Cap verbosity; avoid leaking secrets in logs.

## Troubleshooting
- Oversize message — Shorten or split notes.

## Source of Truth
- Code: src/inspect_agents/tools.py
- Guides: ../guides/tool-umbrellas.md


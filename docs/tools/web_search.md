---
title: "web_search Reference"
status: draft
kind: standard
mode: stateless
owner: docs
---

# web_search

## Overview
- Executes a one-shot web query via a configured provider; returns results.
- Classification: stateless.

## Parameters
- q: string — Query text. Required.
- recency: int — Optional days to filter freshness.
- domains: list[string] — Optional domain allowlist.

## Result Schema
- results: list[object] — Provider-normalized results (title,url,snippet,…).
- errors: list[str]

## Timeouts & Limits
- Execution timeout: TBD. Provider quotas and API timeouts apply.

## Examples
```
Search for a primary source and summarize with citations.
```

## Safety & Best Practices
- Prefer primary sources; include citations; avoid over-trusting snippets.

## Troubleshooting
- Missing API key — Set provider env vars as per quickstart.

## Source of Truth
- Code: src/inspect_agents/tools.py
- Guides: ../getting-started/inspect_agents_quickstart.md


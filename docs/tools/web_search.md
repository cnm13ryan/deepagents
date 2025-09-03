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
- Defaults are defined by Inspect’s standard `web_search` tool and the chosen provider; this repo does not override them. Provider quotas and API timeouts apply.

## Enablement
- Enabled when either:
  - `INSPECT_ENABLE_WEB_SEARCH` is set truthy; or
  - No explicit flag is set but provider credentials are present (`TAVILY_API_KEY`, or `GOOGLE_CSE_API_KEY` + `GOOGLE_CSE_ID`).

## Provider Setup
- Tavily: set `TAVILY_API_KEY`.
- Google CSE: set `GOOGLE_CSE_API_KEY` and `GOOGLE_CSE_ID`.

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

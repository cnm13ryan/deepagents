---
title: "web_browser* Reference"
status: draft
kind: standard
mode: stateful
owner: docs
---

# web_browser_*

## Overview
- Family of navigation/interaction tools backed by a persistent browser/context session.
- Tools include: `web_browser_go`, `web_browser_click`, `web_browser_type_submit`, `web_browser_scroll`, `web_browser_back`, `web_browser_forward`, `web_browser_refresh`.
- Classification: stateful (session id created on first use; reused across calls).

## Parameters
- session_id: string — Optional; if absent, a new session is created.
- action-specific fields — e.g., url, selector, text, delta.

## Result Schema
- snapshot: object — Page state/DOM excerpt/screenshot ref (provider-dependent).
- events: list[object] — Actions performed and outcomes.
- errors: list[str]

## Timeouts & Limits
- Navigation/interaction timeouts: TBD. Session lifetime and parallelism limits: TBD.

## Examples
```
Open a page, click a link, capture content.
```

## Safety & Best Practices
- Avoid navigating to untrusted pages; respect robots and auth requirements.

## Troubleshooting
- Stale session — Retry with a new session_id or use restart action if available.

## Source of Truth
- Code: src/inspect_agents/tools.py
- Guides: ../guides/tool-umbrellas.md


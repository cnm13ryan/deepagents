---
title: "text_editor Reference"
status: draft
kind: standard
mode: stateless
owner: docs
---

# text_editor

## Overview
- In-process JSON-RPC style editor with verbs like `view`, `create`, `str_replace`, `insert`, `undo_edit`.
- Used directly or via proxies from FS tools in sandbox mode.
- Classification: stateless (each call is parameterized; no session handle).

## Parameters
- verb: string — One of the supported editor actions. Required.
- args: object — Verb-specific fields. Required.

## Result Schema
- result: object — Verb-specific response fields.
- errors: list[str]

## Timeouts & Limits
- Defaults are defined by Inspect’s standard `text_editor` tools; this repo does not override them. See Inspect documentation for authoritative limits.

## Enablement
- Disabled by default. Set `INSPECT_ENABLE_TEXT_EDITOR_TOOL=1` and use `INSPECT_AGENTS_FS_MODE=sandbox` for meaningful host‑FS interactions.

## Examples
```
Preview the first 200 lines of a file.
```

## Safety & Best Practices
- Prefer narrow ranges and explicit positions for edits.

## Troubleshooting
- Unknown verb — Check supported verbs and fields.

## Source of Truth
- Code: src/inspect_agents/tools.py
- FS proxy: src/inspect_agents/tools_files.py

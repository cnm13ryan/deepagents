# TODO: Conversation Pruning — Env Toggles + Optional Debug Log

## Context & Motivation
- Purpose: make pruning thresholds configurable and observable without code edits.
- Problem: hardcoded `prune_after_messages=120`, `prune_keep_last=40`; no env knobs or pruning logs.
- Value: tune memory/token usage; debug prune behavior when needed.

## Implementation Guidance
- Examine: `src/inspect_agents/iterative.py` (builder args and prune calls), `src/inspect_agents/_conversation.py` (utility), logging helper `_log_tool_event` in `src/inspect_agents/tools.py` (for consistent logs).
- Grep tokens: `prune_after_messages`, `prune_keep_last`, `INSPECT_MODEL_DEBUG`, `prune_messages(`.

## Scope Definition
- Implement: read `INSPECT_PRUNE_AFTER_MESSAGES` and `INSPECT_PRUNE_KEEP_LAST` when builder args are None; add `INSPECT_PRUNE_DEBUG=1` to emit a single info log per prune with pre/post counts.
- Preserve: default values and behavior when env isn’t set.
- Tests: loop past thresholds, assert tail sizes and one info log appears only under debug.

## Success Criteria
- Behavior: env toggles honored; optional debug logs emitted.
- Tests: green with `pytest -q -k iterative and prune`.
- Perf: no heavy imports; O(1) log payloads.

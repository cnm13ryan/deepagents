# Testing Guide — Limits & Truncation

Covers tool-output truncation envelopes and byte limits.

## What to verify
- Envelope presence and wording when tool output exceeds limit.
- `<START_TOOL_OUTPUT>`/`<END_TOOL_OUTPUT>` markers wrap the truncated payload.
- Bytes inside the envelope equal the configured limit.

## Patterns
- Create a trivial tool returning a large string, call with `max_output=<bytes>`, and assert envelope + payload length.
- Keep assertions byte-precise by measuring `len(payload.encode('utf-8'))`.

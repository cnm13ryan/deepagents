# TODO — Add Counts to Truncation Envelope (outside payload)

## Context & Motivation
- Purpose: Improve clarity for humans and models by stating how many bytes are shown vs. original, without altering payload markers.
- Problem: Current envelope signals truncation but omits the degree of truncation; users must infer from behavior/logs.
- User Impact: Easier debugging and follow‑ups (e.g., request chunking), stable tests because payload markers remain untouched.

## Implementation Guidance
- Examine:
  - `external/inspect_ai/src/inspect_ai/model/_call_tools.py` — `truncate_tool_output` builds the envelope string.
- Grep targets: `<START_TOOL_OUTPUT>`, `<END_TOOL_OUTPUT>`, `TruncatedToolOutput`, `truncate_string_to_bytes`.
- Approach:
  - Keep header and markers as‑is.
  - Add a single line above `<START_TOOL_OUTPUT>`: e.g., `Showing {active_max_output} bytes of original {truncated.original_bytes} bytes.`
  - Do not modify the bytes inside the markers; tests measure payload length.

## Scope Definition
- Implement:
  - Insert counts line into the dedented envelope string before the start marker.
- Modify:
  - `external/inspect_ai/src/inspect_ai/model/_call_tools.py` only.
- Avoid:
  - Changing truncation algorithm or markers; do not move or wrap the payload.

## Success Criteria
- Behavior: When truncation occurs, counts line appears once; payload length inside markers remains unchanged and equals the limit.
- Tests:
  - New integration test: assert presence of the counts line and unchanged payload size.

## Task Checklist
- [ ] Augment envelope string with counts line.
- [ ] Add integration test asserting counts line and payload length.
- [ ] Run `pytest -q -k truncation` and ensure green.


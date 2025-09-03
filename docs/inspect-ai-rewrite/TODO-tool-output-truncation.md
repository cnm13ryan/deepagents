# TODO — Tool Output Truncation

Context & Motivation
- Prevent excessive tool outputs from overwhelming the model; provide a standardized truncated output envelope.

Implementation Guidance
- Truncation: `truncate_tool_output` and `active_generate_config().max_tool_output` in `external/inspect_ai/src/inspect_ai/model/_call_tools.py`

Scope — Do
- [ ] Set default `max_tool_output` via generate config
- [x] Tests: produce oversized tool output; assert the truncation template and byte limits

Scope — Don’t
- Don’t disable truncation globally; allow per-run overrides

Success Criteria
- [x] Long outputs are truncated with the Inspect standard wrapper; model receives clear guidance

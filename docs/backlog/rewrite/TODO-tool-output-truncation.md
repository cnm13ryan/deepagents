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

---

## Considerations & Trade-offs

- Default size: 16 KiB is a balanced guardrail. 8 KiB saves cost but risks clipping useful mid-sections; 32–64 KiB increases fidelity at the expense of context budget and latency.
- Precedence: explicit API arg (`max_output`) > per-run `GenerateConfig.max_tool_output` > environment override (optional) > library fallback (16 KiB).
- Strategy: keep byte-based middle truncation (deterministic across providers); keep screenshot/image outputs untruncated; wrap text with the Inspect envelope markers.
- JSON outputs: truncation can break structure; the envelope communicates truncation but downstream parsing should not assume validity. Prefer tool-level summarization/chunking over raising global caps.
- Unicode: middle truncation may cut multibyte boundaries; acceptable for logs; document the caveat.
- Ops override: consider `INSPECT_MAX_TOOL_OUTPUT` with low precedence and a clear startup log of the effective source. Prefer explicit per-run overrides for determinism in tests.

Recommended default: set `GenerateConfig.max_tool_output = 16 * 1024` and retain the existing function-level fallback to 16 KiB in `truncate_tool_output`.

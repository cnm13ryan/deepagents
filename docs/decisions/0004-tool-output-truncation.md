# docs(truncation): Standardize tool output truncation defaults & envelope
---
Title: D0004 — Tool Output Truncation Defaults
Status: Proposed
Date: 2025-09-03
---

Context
- Inspect enforces tool-output truncation via `truncate_tool_output(...)`, sourcing the limit from the active `GenerateConfig.max_tool_output` and falling back to 16 KiB when unset. The output is wrapped in a stable envelope with `<START_TOOL_OUTPUT>` / `<END_TOOL_OUTPUT>` markers.  
  References: `truncate_tool_output` and `active_generate_config()`  
  external/inspect_ai/src/inspect_ai/model/_call_tools.py, external/inspect_ai/src/inspect_ai/model/_generate_config.py.
- Integration tests in this repo assert both the envelope and strict byte limits within the markers for oversized outputs.

Decision (Proposed)
- Default Limit: Set `GenerateConfig.max_tool_output` default to 16 KiB (16384 bytes). Keep the function-level fallback (also 16 KiB) for safety.
- Precedence: Explicit API arg `max_output` > per-run `GenerateConfig.max_tool_output` > environment override (optional) > library fallback (16 KiB).
- Envelope: Keep the current Inspect wrapper. Optionally include counts (original bytes, shown bytes) outside the payload block in a future enhancement.
- Strategy: Continue byte-based middle truncation (head+tail) for determinism across providers; keep image content untruncated.

Rationale
- Aligns with existing pass-through design: this project defers core policies to Inspect wherever possible; `agents.build_supervisor` forwards options without re-implementing limits.
- Determinism and cost control: 16 KiB preserves useful context while bounding tokens and latency. Middle truncation retains command headers and result tails.
- Low blast radius: matches the current implicit fallback; formalizing the default at the config layer improves transparency.

Trade-offs
- Size: 8 KiB lowers cost but risks dropping useful mid-sections; 32–64 KiB improves fidelity but increases prompt bloat and can hide chatty tool issues.
- Units: Bytes are tokenizer-agnostic and deterministic; token limits vary by model/provider.
- Env Overrides: Convenient for ops but can surprise runs; if added, keep low precedence and log the effective source.
- Unicode: Middle truncation may cut multibyte boundaries; acceptable for logs. Document the caveat; structured tools should summarize rather than dump blobs.

Implementation Notes
- Change `GenerateConfig.max_tool_output` to default to `16 * 1024`; keep existing fallback in `truncate_tool_output` to 16 KiB.
- Do not change `agents.build_supervisor(truncation=...)` semantics (conversation truncation is orthogonal to tool-output truncation).
- Tests already cover envelope+limit behavior when `max_output` is set explicitly; add a smoke test asserting the default applies when not provided.

Rollout
- Document default and override precedence in user guides.
- Optional: add a startup log line indicating effective `max_tool_output` and its source (arg/config/env/default) for easier debugging.


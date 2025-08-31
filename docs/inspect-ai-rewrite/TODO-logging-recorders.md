# TODO — Logging & Recorders

Context & Motivation
- Ensure Inspect transcripts and recorder outputs are enabled, discoverable, and useful for debugging and audits.
- Provide default file-based logging and guidance to read transcripts and event bundles.

Implementation Guidance
- Inspect transcript + spans: `external/inspect_ai/src/inspect_ai/log/_transcript.py`, `util/_span.py`
- File recorder: `external/inspect_ai/src/inspect_ai/log/_recorders/file.py`, `log/_bundle.py`
- Events to expect: `StoreEvent`, `ToolEvent`, span begin/end; approval events are reflected via tool events and decisions.

Scope — Do
- [ ] Choose default recorder(s) and output directory (e.g., `.inspect/logs/`)
- [ ] Initialize recorder at run start; ensure it is active for agent.run
- [ ] Add docs: where logs live; how to open transcripts/bundles
- [ ] Tests assert presence of `StoreEvent` after state changes and `ToolEvent` after tool calls

Scope — Don’t
- Don’t reimplement Inspect logging; configure and document usage

Success Criteria
- [ ] Running examples generate transcript + file bundle
- [ ] Tests parse recent bundle and find StoreEvent + ToolEvent entries

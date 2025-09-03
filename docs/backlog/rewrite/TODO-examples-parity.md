# DONE — Examples Parity (Inspect-native)

Context & Motivation
- Provide working examples mirroring deepagents flows using the new Inspect-native implementation to aid users and serve as smoke tests.

Implementation Guidance
- Read: `examples/` directory for current flows  
  Grep: `create_deep_agent`

- Scope — Do
- [x] Add `examples/inspect/` with:
  - [x] Example 1: minimal run utility (`run.py`); integrates tools and writes transcript
  - [x] Example 2: sub-agent delegation + approval policy demo (show `transfer_to_*` boundary and approval outcomes)
- [x] Update `README.md` with run instructions and submodule note

Scope — Don’t
- Avoid network model calls in examples by default; document how to enable

Success Criteria
- [ ] Examples run locally with minimal setup; instructions accurate

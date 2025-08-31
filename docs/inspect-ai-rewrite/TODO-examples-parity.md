# TODO — Examples Parity (Inspect-native)

Context & Motivation
- Provide working examples mirroring deepagents flows using the new Inspect-native implementation to aid users and serve as smoke tests.

Implementation Guidance
- Read: `examples/` directory for current flows  
  Grep: `create_deep_agent`

Scope — Do
- [ ] Add `examples/inspect/` with:
  - [ ] Example 1: todo + file edit workflow using Store tools + supervisor
  - [ ] Example 2: sub-agent delegation + approval policy demo
- [ ] Update `README.md` with run instructions and submodule note

Scope — Don’t
- Avoid network model calls in examples by default; document how to enable

Success Criteria
- [ ] Examples run locally with minimal setup; instructions accurate


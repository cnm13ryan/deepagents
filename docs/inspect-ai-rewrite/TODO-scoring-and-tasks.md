# TODO — Scoring & Tasks

Context & Motivation
- Enable react() attempts to evaluate submissions using a scorer and continue when incorrect. Provide minimal scoring to test incorrect→retry→correct flows.

Implementation Guidance
- Scoring API: `external/inspect_ai/src/inspect_ai/scorer/_score.py`, `scorer/_metric.py`, `scorer/_common.py`
- react attempts integration: `external/inspect_ai/src/inspect_ai/agent/_react.py` (submission + attempts)

Scope — Do
- [ ] Implement a simple scorer (e.g., non-empty string → 1.0, else 0.0) for tests
- [ ] Provide a tiny task wrapper that attaches the scorer to a sample
- [ ] Tests:
  - [ ] First submit incorrect → react continues with `incorrect_message`
  - [ ] Second submit correct → loop terminates with passing score

Scope — Don’t
- Don’t tie scoring to external datasets yet; keep unit tests isolated

Success Criteria
- [ ] Attempts/score flow exercised; transcript shows both submissions and final pass

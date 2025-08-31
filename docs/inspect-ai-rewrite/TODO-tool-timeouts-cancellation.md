# TODO — Tool Timeouts & Cancellation

Context & Motivation
- Ensure long-running tool calls are bounded and operator cancellations are handled with clear, standard errors.

Implementation Guidance
- Concurrency + cancel scope: `external/inspect_ai/src/inspect_ai/model/_call_tools.py` (TaskGroup, cancel_scope)
- Cancellation outcome and error surface (ToolCallError with `timeout`): same module

Scope — Do
- [ ] Set sensible per-tool/default timeouts; document defaults
- [ ] Expose cancel controls in dev CLI for demos
- [ ] Tests:
  - [ ] Simulate a long-running tool and assert timeout produces a ToolCallError with type `timeout`
  - [ ] Verify transcript includes a note that the tool call was cancelled

Scope — Don’t
- Don’t swallow timeout errors; surface them to the model consistently

Success Criteria
- [ ] Timed-out calls yield standard timeout error messages and transcript events

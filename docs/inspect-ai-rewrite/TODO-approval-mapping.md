# TODO — Tool Approval Mapping (interrupts → ApprovalPolicy)

Context & Motivation
- Recreate deepagents’ human-in-the-loop tool approvals using Inspect’s ApprovalPolicy and approvers.

Implementation Guidance
- Read: `src/deepagents/interrupt.py`  
  Grep: `ToolInterruptConfig`, `allow_accept`, `allow_edit`, `allow_respond`
- Read: `external/inspect_ai/src/inspect_ai/approval/_policy.py`  
  Grep: `policy_approver`, `ApprovalPolicy`, `tools:` patterns

Scope — Do
- [ ] Add `src/inspect_agents/approval.py`:
  - [ ] `def approval_from_interrupt_config(cfg: dict[str, HumanInterruptConfig|bool]) -> Approver`
  - [ ] Map to policy approver(s); implement approve/edit/response behaviors
- [ ] Tests `tests/inspect_agents/test_approval.py`:
  - [ ] Approve → executes original args
  - [ ] Edit → modifies args before execution
  - [ ] Respond → returns synthetic message without executing tool

Scope — Don’t
- Avoid coupling to LangGraph interrupt types; define a local schema

Success Criteria
- [ ] Policies apply to named tools and globs; tests pass


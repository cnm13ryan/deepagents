# DONE — Tool Approval Mapping (interrupts → ApprovalPolicy)

Context & Motivation
- Recreate deepagents’ human-in-the-loop tool approvals using Inspect’s ApprovalPolicy and approvers.

Implementation Guidance
- Read: `src/deepagents/interrupt.py`  
  Grep: `ToolInterruptConfig`, `allow_accept`, `allow_edit`, `allow_respond`
- Read: `external/inspect_ai/src/inspect_ai/approval/_policy.py` and `_apply.py`  
  Grep: `policy_approver`, `ApprovalPolicy`, `init_tool_approval`, `apply_tool_approval`
  Note: Inspect approvals support decisions {approve, modify, reject, terminate}. There is no built‑in “respond” pathway.

Scope — Do
- [x] Add `src/inspect_agents/approval.py`:
  - [x] `def approval_from_interrupt_config(cfg: dict[str, Any]) -> list[ApprovalPolicy]` producing policy entries
  - [x] Provide a helper to call `init_tool_approval(policies)` before running the agent
- [x] Tests (`tests/integration/inspect_agents/test_approval.py`,
  `tests/integration/inspect_agents/test_approval_chains.py`):
  - [x] Approve → original args execute
  - [x] Modify → tool call arguments changed before execution
  - [x] Reject → prevents execution
  - [x] Terminate → aborts sample (terminate decision)

Scope — Don’t
- Do not attempt to simulate “respond” within approvals; if needed, design a separate lightweight `respond()` tool in a future feature.

Success Criteria
- [x] Policies apply to named tools and globs; tests pass
- [x] Approval policies are activated by calling `init_tool_approval(...)` before `agent.run(...)`

Recommended Defaults
- Policy presets:
  - `ci`: auto-approve by default; escalate/deny network and host FS tools.
  - `dev`: auto-approve common tools; prompt for destructive or networked actions.
  - `prod`: human approve for sensitive tools; allow auto-approve for harmless operations.
- Consider a future, approver-only `respond()` tool if “reply without execution” becomes a common need.

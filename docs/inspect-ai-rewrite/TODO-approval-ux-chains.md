# done — TODO — Approval UX & Chains

Context & Motivation
- Deliver a safe, ergonomic human-in-the-loop flow: appropriate approver chains (auto→human), redacted views, and predictable decisions.

Implementation Guidance
- Approval pipeline: `external/inspect_ai/src/inspect_ai/approval/_policy.py`, `_apply.py`
- Default viewer and redaction opportunities: `_apply.default_tool_call_viewer`

Scope — Do
- [ ] Configure policy presets (ci/dev/prod) and document them
- [ ] Implement argument redaction for sensitive fields in viewer
- [ ] Chain approvers (e.g., auto approve unless pattern matches → escalate to human)
- [ ] Tests: approve/modify/reject/terminate flows; viewer redaction present

Scope — Don’t
- Don’t attempt “respond” inside approval decisions; consider separate tool later

Success Criteria
- [ ] Policies applied via `init_tool_approval(...)` before run
- [ ] Redacted viewer content is used in human panels/consoles

# Handoff Exclusivity — Open Questions

Last updated: 2025-09-04

This document tracks open questions and decision proposals related to the default enforcement of “first handoff wins” (aka handoff exclusivity) in approval presets.

Context

- Presets: `approval_preset("dev"|"prod")` currently include the `handoff_exclusive_policy()` approver as part of the returned policy list. The CI preset intentionally omits it. This enables safer defaults by preventing multiple handoffs in a single assistant turn.
- Policy Engine: Inspect’s `policy_approver` processes policies in order and returns on the first decision that is not `"escalate"`.
- Approver Behavior: The exclusivity approver approves only the first `transfer_to_*` tool call from the most recent assistant message; all other tool calls in that same message are rejected with an “exclusivity” explanation. It approves everything if no handoff is present.

Why this matters

Exclusivity is intended to be a global guard: when a handoff is present in a batch, “only the first handoff runs” and non‑handoff tools should be skipped. Ordering and observability details determine whether the guard is actually enforced and whether operators can audit it.

---

# Tool Output Truncation — Env Override + One‑Time Effective Limit Log (Open)

Last updated: 2025-09-04

Context

- Goal: Allow operators/CI to override the upstream tool-output envelope size via env and log the effective limit once per run to aid incident analysis and deterministic test tuning.
- Implementation (current): On the first repo-local tool log, emit a one-time `tool_event` with `{tool:"observability", phase:"info", effective_tool_output_limit:<int>, source:"env|default"}` and, if `GenerateConfig.max_tool_output` is unset, optionally apply `INSPECT_MAX_TOOL_OUTPUT` to the active config. This preserves precedence: explicit arg > `GenerateConfig.max_tool_output` > `INSPECT_MAX_TOOL_OUTPUT` > default `16 KiB`. 〖F:src/inspect_agents/tools.py†L64-L135〗 〖F:src/inspect_agents/tools.py†L178-L181〗
- Docs: Added `INSPECT_MAX_TOOL_OUTPUT` to environment reference with examples and the one-time log format. 〖F:docs/reference/environment.md†L198-L206〗
- Tests: Added unit coverage to assert single-emission behavior and env/default resolution. 〖F:tests/unit/inspect_agents/test_effective_tool_output_limit_log.py†L1-L21〗 〖F:tests/unit/inspect_agents/test_effective_tool_output_limit_log.py†L23-L46〗 〖F:tests/unit/inspect_agents/test_effective_tool_output_limit_log.py†L49-L91〗

Why this matters

Operators need a consistent way to see and control the tool-output envelope across environments without code changes, while keeping explicit per-run settings authoritative. The one-time log provides an anchor for debugging truncation symptoms without adding noise.

Open Question A — Source Label Granularity

- Problem
  - The one-time log currently reports `source` as `env` when `INSPECT_MAX_TOOL_OUTPUT` is applied, otherwise `default`. It does not distinguish cases where a non-default `GenerateConfig.max_tool_output` or a per-call `max_output` argument is in effect (even though those take precedence and will be reflected in actual truncation behavior).
- Options
  - A1) Keep minimal labels: `env|default` only (current). Simple and stable for log parsers.
  - A2) Expand to `arg|config|env|default` based on the highest-precedence contributor at time of first log.
  - A3) Emit `sources: {arg:bool, config:bool, env:bool, default:bool}` for richer diagnostics.
- Considerations
  - A2/A3 require detecting explicit per-call args at the time of first log, which may not exist yet; emitting after the first actual truncation event would be more accurate but later in time.
- Proposal
  - Decide whether operator value outweighs the added coupling. If yes, prefer A2 on the first observed truncation (not merely first tool log) to reflect true active source.

Open Question B — Emission Timing and Shape

- Problem
  - We emit a dedicated one-time `tool_event` before the first real tool `start` event. Alternative is to piggyback fields onto the first `start` event.
- Options
  - B1) Separate `observability` event (current): discoverable and does not affect existing event schemas.
  - B2) Attach fields to first real tool `start` event: fewer lines but couples semantics and may break assertions on event shapes.
- Proposal
  - Keep B1 unless there is a strong requirement to minimize log lines; document the event as stable operator signal.

Open Question C — Config Mutation Contract

- Problem
  - We currently set the active `GenerateConfig.max_tool_output` from env only when it is `None`, to preserve precedence. Should we make this behavior explicit in public docs and guarantee it won’t override future preset defaults?
- Options
  - C1) Keep behavior but document it as a contract (env never overrides non-None config; per-call arg always wins).
  - C2) Never mutate active config; only log the effective env. This simplifies semantics but forfeits the fleet-wide knob unless the upstream call path checks env.
- Proposal
  - Prefer C1 (current). Document the precedence and mutation point clearly; add a guard test asserting config remains authoritative when set.

Open Question D — Default Value to Log

- Problem
  - When `INSPECT_MAX_TOOL_OUTPUT` is unset and config is `None`, we log `16384` bytes (16 KiB). If upstream changes its fallback or begins defaulting the config, our logged value might diverge.
- Options
  - D1) Continue logging `16384` as the repo default (current) and accept drift risk.
  - D2) Resolve from `active_generate_config()` if non-`None`, else defer emission until first truncation where upstream’s chosen default can be observed and logged.
- Proposal
  - Prefer D2 if accuracy is critical; otherwise keep D1 for earlier visibility.

Open Question E — Multi‑Process/Multi‑Worker Semantics

- Problem
  - The “once” guard is process-local. In multi-worker runs, the line will appear once per process.
- Options
  - E1) Accept per-process once (current).
  - E2) Add a file/FD-based lock to deduplicate across workers (heavier and can block).
  - E3) Rely on centralized transcript aggregation for dedupe.
- Proposal
  - Keep E1 and document expected multiplicity; revisit if operators request global dedupe.

Open Question F — Invalid Env Handling

- Problem
  - Invalid values (non-integer or negative) are silently ignored.
- Options
  - F1) Keep silent ignore (current) to avoid noisy logs.
  - F2) Emit a single warning `tool_event` noting the invalid value and the fallback path.
- Proposal
  - Adopt F2 if misconfiguration becomes a common source of confusion.

Next Steps

1) Decide on source label granularity (A) and emission timing (B); update implementation and docs accordingly.
2) Document the config mutation contract (C) in environment reference and add a small precedence test that sets config and confirms env is ignored.
3) Choose default logging policy (D) — fixed 16 KiB vs defer-to-observed — and adjust tests.
4) Evaluate demand for cross-worker dedupe (E) and invalid-env warnings (F) post-usage.

Open Question 1 — Policy Precedence of Exclusivity

- Problem
  - `policy_approver` short‑circuits on the first non‑escalate result. If exclusivity is appended after a permissive gate (e.g., a dev gate that returns `approve` for non‑sensitive tools), exclusivity may never run for those calls. This could permit non‑handoff tools to execute in the same batch as a handoff, violating “first handoff wins.”

- Current Behavior (today)
  - In `dev`: policies are ordered as a permissive gate for non‑sensitive tools, followed by a reject‑all, with exclusivity appended. For non‑sensitive tools, the gate returns `approve`, so exclusivity doesn’t run. For sensitive tools, the gate escalates and the reject‑all short‑circuits before exclusivity.
  - In `prod`: the gate returns `approve` for non‑sensitive tools and `terminate` for sensitive; exclusivity appended afterwards may not run for non‑sensitive tools.

- Implication
  - Exclusivity is not guaranteed to apply to non‑sensitive tools when a handoff appears in the same assistant turn, depending on policy order.

- Options
  - A) Place exclusivity first in the preset lists, ahead of approval/termination gates. Ensures exclusivity evaluates every call and can reject non‑handoff tools in a handoff batch before permissive gates approve them.
  - B) Teach gates (dev/prod) to detect “handoff present in message/history” and return `escalate` in that case. This preserves existing order but couples gates to exclusivity semantics and duplicates logic.
  - C) Apply exclusivity at the approval apply layer (global hook) so it runs regardless of policy order. This may require upstream changes and is heavier‑weight.
  - D) Keep the current order but accept that exclusivity only constrains handoff tools themselves, not non‑handoff calls. This weakens the safety guarantee.

- Proposal
  - Prefer Option A: position `handoff_exclusive_policy()` before other preset approvers for `dev` and `prod`. This guarantees evaluation and keeps concerns separated: exclusivity = batch‑level guard; gates = sensitivity decisions.

- Acceptance Criteria
  - Integration test using the real `policy_approver`: with an assistant message containing `[transfer_to_researcher, read_file]`, the `read_file` call is rejected due to exclusivity; only the first handoff is approved. Repeat for both `dev` and `prod`.

<details>
<summary>✅ Answer Found in Implementation</summary>

**Finding**: `approval_preset("dev"|"prod")` now places `handoff_exclusive_policy()` first, before the permissive/termination gates, ensuring exclusivity is evaluated on every call in the batch.
**Evidence**: Presets return `handoff_exclusive_policy() + [...]` with comments indicating "enforce handoff exclusivity BEFORE" the gates. 〖F:src/inspect_agents/approval.py†L176-L186〗 Unit test asserts the exclusivity approver is present in both presets and verifies its effect on a mixed batch. 〖F:tests/unit/inspect_agents/test_preset_handoff_exclusivity.py†L86-L92〗 〖F:tests/unit/inspect_agents/test_preset_handoff_exclusivity.py†L123-L131〗 Integration test with the real Inspect policy engine confirms first‑handoff approval and rejection of subsequent handoff and non‑handoff calls. 〖F:tests/integration/inspect_agents/test_handoff_exclusivity_integration.py†L45-L66〗
**Conclusion**: Option A (place exclusivity first) has been implemented; the precedence issue is resolved.

</details>

---

Open Question 2 — Transcript Assertions for Exclusivity Skips

- Problem
  - We currently rely on repo‑local logging (`tools._log_tool_event`) for operator visibility when exclusivity skips calls. Tests assert on that logger. There is optional support to emit a standardized transcript `ToolEvent` for “skipped due to handoff,” but we don’t assert on it.

- Why add transcript assertions?
  - Transcript events are provider‑agnostic, show up in Inspect’s traces, and improve incident forensics. Asserting their presence ensures future changes don’t regress operator visibility.

- Options
  - A) Add unit tests that stub `inspect_ai.log._transcript.transcript()` and assert a `ToolEvent` is emitted with metadata: `selected_handoff_id`, `skipped_function`, `source=policy/handoff_exclusive`.
  - B) Add an integration test wiring `policy_approver` + apply layer and assert the emitted transcript event for a skipped non‑handoff call.
  - C) Defer transcript assertions and rely solely on repo‑local logs (lowest effort, but less portable across environments).

- Proposal
  - Start with Option A in unit tests (cheap, deterministic), and add Option B as a follow‑up integration test once policy precedence is finalized.

- Acceptance Criteria
  - Failing test if the transcript emission changes schema or disappears; success means one “skipped due to handoff” `ToolEvent` per skipped call with the expected metadata fields.

<details>
<summary>✅ Answer Found in Implementation</summary>

**Finding**: The exclusivity approver emits a standardized transcript `ToolEvent` for each skipped call, and tests assert its presence and metadata.
**Evidence**: `handoff_exclusive_policy()` synthesizes a `ToolEvent` with `pending=False`, `error=ToolCallError("approval", "Skipped due to handoff")`, and metadata `selected_handoff_id`, `skipped_function`, `source="policy/handoff_exclusive"`. 〖F:src/inspect_agents/approval.py†L282-L303〗 End-to-end test asserts two such events for skipped non‑handoff tools. 〖F:tests/integration/inspect_agents/test_handoff_exclusive_end_to_end.py†L100-L112〗 Unit test also validates event shape and source. 〖F:tests/unit/inspect_agents/test_handoff_exclusive_policy.py†L174-L186〗
**Conclusion**: Transcript assertions are in place (Options A/B effectively adopted); acceptance criteria satisfied by unit and integration coverage.

</details>

Detailed Open Questions — Transcript “Skipped” ToolEvents

1) Error code strategy (type vs mapping vs docs)
- Context: ADR 0005 specifies `error.code="skipped"` for skipped calls; Inspect’s ToolCallError currently does not define a `"skipped"` variant. We emit `ToolCallError("approval", "Skipped due to handoff")` and attach attribution via metadata. 〖F:docs/adr/0005-tool-parallelism-policy.md†L22-L25〗 〖F:external/inspect_ai/src/inspect_ai/tool/_tool_call.py†L61-L74〗 〖F:src/inspect_agents/approval.py†L282-L303〗
- Options:
  - Upstream type: add `"skipped"` to Inspect’s `ToolCallError` union; update producers/consumers and tests. Pros: explicit, easy to query. Cons: upstream change and compatibility churn.
  - Export-time mapping: keep `type="approval"` in transcripts; when exporting logs, map events where `metadata.source=="policy/handoff_exclusive"` to `{code:"skipped", message:...}` for JSON consumers. Pros: minimal blast radius now. Cons: in-memory vs exported semantics differ. Candidate hook: `write_transcript()` serialization. 〖F:src/inspect_agents/logging.py†L32-L38〗 〖F:src/inspect_agents/logging.py†L41-L60〗
  - Docs-only: document `type="approval"` as the canonical representation for policy-driven skips; require consumers to key off `metadata.source` and `selected_handoff_id` rather than a new code.
- Proposal: adopt export-time mapping immediately for operator logs; pursue upstream addition in parallel if broader ecosystem wants `"skipped"` as first-class.

⚠️ Still Open - Requires Decision

- Partial implementation only: events use `ToolCallError(type="approval")`; no export‑time mapping to `{code:"skipped"}` exists in transcript writer. `write_transcript()` currently serializes events as-is with light redaction. 〖F:src/inspect_agents/approval.py†L291-L303〗 〖F:src/inspect_agents/logging.py†L32-L38〗 〖F:src/inspect_agents/logging.py†L41-L60〗

2) Event contract stability (pending, metadata)
- Context: Policy synthesizes `ToolEvent` with `pending=False` and metadata: `selected_handoff_id`, `skipped_function`, and `source:"policy/handoff_exclusive"`. Tests assert this shape. 〖F:src/inspect_agents/approval.py†L291-L303〗 〖F:tests/integration/inspect_agents/test_handoff_exclusive_end_to_end.py†L78-L100〗
- Decision to confirm: treat the following as stable for v1
  - `pending=False` always set on synthesized skip events.
  - `metadata` must include `selected_handoff_id`, `skipped_function`, `source`.
- Rationale: explicit pending state avoids ambiguity; stable metadata keys support analytics and cross-run correlation.

<details>
<summary>✅ Answer Found in Implementation</summary>

**Finding**: Exclusivity approver sets `pending=False` and includes `selected_handoff_id`, `skipped_function`, and `source` in `metadata`; tests assert these fields.
**Evidence**: Event construction sets `pending=False` and metadata keys. 〖F:src/inspect_agents/approval.py†L291-L303〗 Integration test filters transcript by `source=="policy/handoff_exclusive"` and validates fields. 〖F:tests/integration/inspect_agents/test_handoff_exclusive_end_to_end.py†L100-L112〗
**Conclusion**: Event contract for v1 is implemented and covered by tests.

</details>

3) message_id timing (now vs v2 executor pre-scan)
- Context: `ToolEvent.message_id` links to a `ChatMessageTool` when one exists. For policy-synthesized skips, no conversation message is added by design; in executor pre-scan (v2) there will also be no `ChatMessageTool` for skipped calls. 〖F:external/inspect_ai/src/inspect_ai/log/_transcript.py†L242-L244〗 〖F:docs/adr/0005-tool-parallelism-policy.md†L22-L25〗
- Options:
  - Defer: keep `message_id=None` for policy-synthesized skips in v1; revisit when implementing v2 pre-scan to decide if a synthetic, trace-only id adds value.
  - Add now: populate `message_id` with the selected handoff’s message id to aid joins. Risk: could imply a 1:1 relation that doesn’t exist; skipped calls have no ChatMessageTool.
- Recommendation: defer; document `message_id` as optional and typically absent for skip events in v1.

<details>
<summary>✅ Answer Found in Implementation</summary>

**Finding**: Policy‑synthesized skip events omit `message_id` (left `None`), matching the defer recommendation.
**Evidence**: `ToolEvent` created without a `message_id` attribute in exclusivity approver. 〖F:src/inspect_agents/approval.py†L291-L303〗 Transcript data model documents `message_id` as the ChatMessageTool linkage, optional by default. 〖F:external/inspect_ai/src/inspect_ai/log/_transcript.py†L242-L244〗
**Conclusion**: v1 behavior is to leave `message_id` unset for policy‑synthesized skips; no synthetic linkage is created.

</details>

---

Open Question 3 — Unit Test Key: Approver Names vs Registry Tags

- Problem
  - The new preset-order unit test asserts approver function names (e.g., `"approver"`, `"dev_gate"`, `"reject_all"`, `"prod_gate"`). Function names may change in refactors, causing brittle tests. 〖F:tests/inspect_agents/test_approval_preset_order.py†L24-L36〗

- Current Behavior
  - Presets prepend the exclusivity approver (`approver`) before gates in `dev`/`prod`. 〖F:src/inspect_agents/approval.py†L176-L187〗 Gate functions are defined as `dev_gate`, `reject_all`, and `prod_gate`. 〖F:src/inspect_agents/approval.py†L151-L169〗

- Options
  - A) Keep asserting function names (simplest; fragile on rename).
  - B) Assert on Inspect registry tags (e.g., `preset/dev_gate`, `preset/prod_gate`, `policy/handoff_exclusive`) if tags are retrievable from the `ApprovalPolicy` or approver function at runtime.
  - C) Behavior-first: assert order indirectly by executing a minimal `policy_approver` pass over representative tool calls and verifying which approver handled the decision (requires capturing approver identity via logging or metadata).
  - D) Hybrid: name assertion for order + one behavior assertion to validate effectiveness.

- Decision Needed
  - Choose the primary assertion mechanism for long-term robustness (Names vs Registry Tags vs Behavior).

---

Open Question 4 — Preset Coverage Beyond dev/prod

- Problem
  - Today the order test targets `dev`, `prod`, and asserts `ci` remains permissive. Future presets (e.g., `staging`, `demo`) may be introduced; should exclusivity be first for all non-`ci` presets, and should tests be parameterized accordingly?

- Options
  - A) Enforce exclusivity-first in all non-`ci` presets; parameterize the test to iterate known presets.
  - B) Limit to `dev`/`prod` only; require explicit decisions for any new presets.
  - C) Add a helper in code: `approval_preset_should_enforce_exclusivity(preset) -> bool` and assert that contract in tests.

- Decision Needed
  - Define policy for future presets and, if (A), add a parameterized test to guard it.

---

Open Question 5 — When to Un‑XFail Integration Test

- Problem
  - The targeted integration test `test_handoff_with_other_tool_only_handoff_executes` remains `xfail`. With exclusivity-first now implemented in presets, should we un‑xfail immediately or wait for a pinned Inspect version and broader CI coverage?

- Current Signal
  - Running the targeted test shows `XFAIL` with message: “Handoff should cancel/skip other tool calls in same turn.” 〖F:tests/integration/inspect_agents/test_parallel.py†L76-L119〗

- Options
  - A) Un‑xfail now and ensure CI pins an Inspect version that guarantees policy semantics.
  - B) Keep `xfail` until a release note explicitly records the preset ordering change and downstream teams have upgraded.
  - C) Gate un‑xfail behind an env flag (e.g., `INSPECT_ENABLE_EXCLUSIVITY_FIRST=1`) to allow staged rollout.

- Decision Needed
  - Choose timing and gating for un‑xfailing the integration test.

---

Open Question 6 — Approval Log Ordering Guarantees

- Problem
  - With exclusivity evaluating first, skip decisions and associated logs/transcript events may occur before gate logs. Do we want to document and guarantee a specific ordering for operator expectations and tooling that scrapes logs?

- Current Behavior
  - Exclusivity returns `escalate` when not applicable (no context/no handoff) to allow gates to decide, avoiding extra logs in non‑handoff batches. 〖F:src/inspect_agents/approval.py†L253-L261〗 When a handoff is present, exclusivity logs a repo‑local event and emits a transcript `ToolEvent` for skipped calls before returning `reject` with explanation. 〖F:src/inspect_agents/approval.py†L268-L311〗

- Options
  - A) Specify ordering: when a handoff is present, exclusivity skip event(s) precede any gate decisions for that batch; skipped calls produce no gate logs.
  - B) No strict ordering guarantee beyond “a skip event is emitted”; tooling should not rely on inter-policy log ordering.
  - C) Provide structured metadata (e.g., `source="policy/handoff_exclusive"`, `selected_handoff_id`) and recommend consumers key off metadata rather than line order.

- Decision Needed
  - Define the operator-visible contract for log/transcript ordering and metadata reliance.


Next Steps

1) Decide policy order for `dev`/`prod` presets (recommend: exclusivity first).
2) Add integration tests that execute through `policy_approver` to validate exclusivity under real short‑circuit semantics.
3) Add transcript‑level assertions to complement existing repo‑local log checks.

Status Update — 2025-09-04

- Added integration test using the real Inspect policy engine: `tests/integration/inspect_agents/test_handoff_exclusivity_integration.py`.
  - Mixed batch `[transfer_to_researcher, transfer_to_writer, read_file]` validates:
    - First handoff → approve.
    - Subsequent handoff and non‑handoff → reject with exclusivity explanation.
  - Scope: exercises exclusivity in isolation (not via presets) to confirm core semantics against `policy_approver`.

Next Steps (updated)

1) Decide policy order for `dev`/`prod` presets (recommend: exclusivity first).
2) Add preset‑aware integration tests via `approval_preset('dev'|'prod')` to pin behavior under short‑circuit semantics.
3) Add transcript‑level assertions (unit first; optional integration) for skipped calls.

---

# Parallel Tool Kill‑Switch — Open Questions

Last updated: 2025-09-04

Context

- Purpose: Provide an operator kill‑switch to disable parallel execution of non‑handoff tools at runtime for safer incident response and deterministic sequencing.
- Implementation (current): An approval policy `parallel_kill_switch_policy()` is included in `dev`/`prod` presets (not `ci`). When `INSPECT_DISABLE_TOOL_PARALLEL` is truthy and a single assistant turn contains multiple tool calls with no handoff, only the first non‑handoff call is approved; others are rejected. If a handoff is present, the policy escalates so `handoff_exclusive_policy()` governs. 〖F:src/inspect_agents/approval.py†L173-L191〗 〖F:src/inspect_agents/approval.py†L322-L406〗
- Observability: On rejections, a repo‑local `tool_event` with `tool="parallel_kill_switch"` and a standardized transcript `ToolEvent` (`metadata.source="policy/parallel_kill_switch"`) are emitted.

Why this matters

The kill‑switch offers a fast, low‑blast‑radius control to tame concurrency during incidents. Details around naming, preset wiring, semantics, and telemetry affect operator experience and downstream consistency.

---

Open Question A — Canonical Env Name and Deprecation Plan

- Decision so far: Standardize on `INSPECT_DISABLE_TOOL_PARALLEL` (matches backlog). Keep `INSPECT_TOOL_PARALLELISM_DISABLE` as a legacy alias for now. 〖F:docs/reference/environment.md†L131-L136〗
- Open decisions:
  - Should we emit a one‑time deprecation log when the legacy alias is used? If yes, where (approval policy vs startup), and what text?
  - Removal timeline: propose warning now, remove alias no earlier than N minor versions or after date YYYY‑MM.

---

Open Question B — Exact Semantics Under the Flag

- Current behavior: Approve only the first non‑handoff call in the batch; reject subsequent non‑handoff calls. Escalate (no decision) when a handoff is present so exclusivity governs. 〖F:src/inspect_agents/approval.py†L376-L406〗
- Alternatives:
  - “Simple mode”: reject all non‑handoff calls in any multi‑call batch (stricter, easier to reason about, but more disruptive).
  - Model‑layer disable: also (or instead) set provider config `parallel_tool_calls=False` upstream when flag is set, preventing concurrent scheduling even if approvals are bypassed.
- Decision needed: keep “first non‑handoff only” as default? introduce an optional stricter mode (e.g., `INSPECT_DISABLE_TOOL_PARALLEL_STRICT=1`)? also add a model‑layer guard for belt‑and‑suspenders?

---

Open Question C — Preset Wiring Strategy

- Current: Policy is part of `dev`/`prod` presets; env‑gated; `ci` unchanged. 〖F:src/inspect_agents/approval.py†L173-L191〗
- Alternatives:
  - Provide a separate preset variant (e.g., `dev_kill_switch`, `prod_kill_switch`) to decouple code presence from env gating.
  - Make it global (always evaluated) but env decides behavior (status quo), yields simpler ops (just export/unset env).
- Decision needed: retain inclusion in `dev`/`prod`, or introduce explicit variants? If variants are added, ensure docs/tests are updated accordingly.

---

Open Question D — Telemetry and Operator Signals

- Current: per‑call skip events via repo logger and transcript with `source="policy/parallel_kill_switch"`.
- Options:
  - Emit a run‑level one‑time info event (e.g., `policy/parallel_kill_switch activated`) when the flag is first observed.
  - Add counters/metrics hooks (skipped_calls, first_allowed_id frequency) for dashboards.
  - Surface in UI: annotate the run header that parallel tool execution is disabled.
- Decision needed: which signals are required for incidents, and where they should appear (logs, transcript, UI, metrics).

---

Open Question E — Runtime Toggle Scope

- Current: Env is checked at approval time, making the switch dynamic per turn.
- Alternatives: Snapshot once per run (deterministic across a run), or allow per‑agent override.
- Decision needed: prefer fully dynamic (simpler ops) vs run‑snapshot (predictable behavior for long runs).

---

Open Question F — Interactions with Handoff Exclusivity and Ordering

- Current: `handoff_exclusive_policy()` precedes the kill‑switch in presets; the kill‑switch escalates when a handoff is detected, ensuring exclusivity governs handoff batches. 〖F:src/inspect_agents/approval.py†L176-L189〗
- Decision needed: codify and test this ordering as an invariant (add a unit asserting preset policy names/ordering), and document in operator runbooks.

---

Open Question G — Multi‑Turn Semantics

- Current: The policy scope is one assistant message (batch) at a time; there is no cross‑turn throttling.
- Consideration: Do we need a stricter emergency mode that enforces “one tool per turn” or “no parallel calls across consecutive turns” at the conversation level?
- Decision needed: clarify desired scope for incident playbooks.


# Testing Strategy — Inspect-AI Source of Truth (Open Questions)

Date: 2025-09-04

Context

- Tests must target the installed site‑packages `inspect_ai`, not the vendored
  copy under `external/inspect_ai/`. This policy is documented in `tests/README.md`.
- `tests/conftest.py` adds only `src/` to `sys.path` and prints where `inspect_ai`
  resolves from in the pytest header to aid debugging.
- A shared fixture `approval_modules_guard` now snapshots originals of
  `inspect_ai.approval._apply|_policy|_approval` and restores them after a test
  that stubs those modules, preventing cross‑test contamination.

Why this matters

- Mixing vendored and installed `inspect_ai` introduces subtle type/schema
  mismatches (e.g., Pydantic models, dataclasses) and flaky behavior. Central
  cleanup of stubs avoids order‑dependent failures.

Questions

1) Make `approval_modules_guard` autouse?
   - Pros: Eliminates opt‑in burden; hardens against leaks everywhere.
   - Cons: Slight overhead; could mask intentionally long‑lived shims in rare
     integration tests.
   - Option: Enable autouse only for `tests/unit/inspect_agents/` where stubs
     are common; keep opt‑in elsewhere.

2) CI enforcement of installed‑only policy?
   - Proposal: Add a CI‑only assertion that fails the run if
     `inspect_ai.__file__` contains `/external/inspect_ai/`.
   - Alternative: Keep as a visible header warning only.

3) Pre‑commit/static checks?
   - Proposal: Add a simple grep‑based pre‑commit to forbid
     `external/inspect_ai/` imports in tests and to flag `teardown_module`
     patterns that delete `inspect_ai.approval*` without using the shared
     fixture.

4) Transcript ToolEvent for exclusivity skips — required vs optional?
   - Today: tests always assert the repo‑local logger event; transcript event
     assertion is optional (assert if present).
   - Option A: Keep optional until we pin an Inspect version that guarantees
     skip‑event semantics.
   - Option B: Make transcript assertion required in CI once a minimum Inspect
     version is pinned.

Open Items — Needs Decision

- Autouse scope for `approval_modules_guard` (package‑wide vs per‑directory).
- Whether to hard‑fail CI on vendor resolution vs warn only.
- Whether to introduce pre‑commit rules for vendor imports and global teardown
  patterns.
- When to promote transcript skip event assertion from optional → required.

---

# YAML Limits Schema — Open Questions

Date: 2025-09-04

Context

- We added a minimal YAML schema for runtime limits and a parser that returns Inspect `Limit` objects from `load_and_build`, then wired those limits through to `run_agent`. The parser currently supports three core types: `time`, `message`, and `token`.
- The minimal spec accepts `type` + `value`, with forgiving aliases (`seconds` for time; `max|limit|tokens|messages` for token/message). Invalid entries raise `ValueError` surfaced by the loader.

Why this matters

- Declarative limit control enables reproducible runs and CI defaults without changing code. Keeping the schema small helps portability and reduces maintenance.

Questions

- Should we keep only `type`+`value`, or continue to accept the convenience aliases for ergonomics?
- How do we represent “unlimited” explicitly (e.g., `null` vs omit `value`) and normalize to `None` consistently across types?
- Do we want a discriminated union schema in docs, or keep the parser permissive and document a canonical form to encourage portability?

Options

- Strict canonical form only: require `{type, value}`; reject aliases. Pros: clarity and portability. Cons: less ergonomic YAML.
- Permissive with normalization (current): accept a small set of aliases, normalize internally to Inspect limits. Pros: user-friendly; Cons: future expansion may collide with new keys.
- Versioned schema tag: add optional `schema: v1` at root to allow future breaking changes; document canonical keys and deprecate aliases over time.

Risks/Notes

- Forward-compatibility: accepting many aliases today can constrain future evolution; limit the alias set and document the canonical form prominently in README examples.
- Error messages: ensure `ValueError`s are actionable (include index and offending keys).

Recommendation

- Keep the minimal alias set for v1 and document the canonical `{type, value}` form. Prefer canonical form in examples; note that aliases may be deprecated in a future schema version.

<details>
<summary>✅ Answer Found in Implementation</summary>

**Finding**: YAML parser accepts a minimal alias set and normalizes to Inspect limits.
**Evidence**: `_limit_from_dict` accepts `{type,value}` plus aliases: `seconds` for time; `max|limit|messages|tokens` for message/token. 〖F:src/inspect_agents/config.py†L92-L107〗
**Conclusion**: “Permissive with normalization (current)” is implemented; canonical `{type,value}` remains supported.

</details>

⚠️ Still Open - Requires Decision

- “Unlimited” representation is inconsistent across types: message/token accept `None` to mean unlimited; time requires a numeric `value` and raises if absent. Decide whether to allow `null`/omitted for time and normalize to `None` for parity. 〖F:src/inspect_agents/config.py†L94-L97〗 〖F:src/inspect_agents/config.py†L100-L107〗

⚠️ Still Open - Requires Decision

- No versioned schema tag is recognized; root `schema: v1` is ignored by the loader/parser today. Consider introducing a tag and documenting canonical keys while deprecating aliases over time. 〖F:src/inspect_agents/config.py†L112-L127〗 〖F:src/inspect_agents/config.py†L65-L76〗

---

# Runner API for Limit Errors — Open Questions

Date: 2025-09-04

Context

- Inspect’s agent runner (`inspect_ai.agent._run.run`) returns `(state, LimitExceededError|None)` when `limits` are supplied (uses `apply_limits(..., catch_errors=True)`).
- Our thin wrapper `inspect_agents.run.run_agent` forwards `limits` but currently returns only the state, discarding the error when a tuple is received. This preserves a simple API but hides the cause when a limit is hit unless callers inspect logs.

Why this matters

- Some applications need to branch on “limit hit” vs normal completion (e.g., retry with higher budget, emit metrics, or surface a specific message to users) without parsing logs.

Questions

- Should `run_agent` surface the `LimitExceededError` (return the tuple) or raise it? If so, how to avoid breaking existing callers?
- Is an opt-in flag (`return_limit_error: bool = False` or `raise_on_limit: bool = False`) preferable to preserve backward compatibility?

Options

- Status quo: keep returning only the state; rely on transcript/logs for visibility. Pros: no API change; Cons: callers cannot branch without extra work.
- Tuple propagation: return `(state, err)` when limits are provided. Pros: mirrors Inspect; Cons: API change for current callers.
- Exception mode: raise `LimitExceededError` when exceeded (opt-in flag). Pros: control-flow friendly; Cons: diverges from Inspect default and complicates examples.

Risks/Notes

- Backward compatibility: changing the return type is a breaking change; an opt-in kwarg mitigates it.
- Documentation: examples and README need to show handling when the option is enabled.

Recommendation

- Add an optional `return_limit_error: bool = False` parameter to `run_agent` in a follow-up. When True and limits are supplied, return `(state, err)`; otherwise, preserve current behavior. Update examples to print a concise “limit hit” line when `err` is not `None`.

<details>
<summary>✅ Answer Found in Implementation</summary>

**Finding**: `run_agent(...)` now supports opt‑in propagation of limit errors via `return_limit_error` and `raise_on_limit` flags while preserving backward compatibility by default.
**Evidence**: Function signature includes `return_limit_error: bool = False` and `raise_on_limit: bool = False`; when Inspect returns `(state, err)`, code optionally raises on limit or returns `(state, err)` when requested, else returns state only. 〖F:src/inspect_agents/run.py†L11-L13〗 〖F:src/inspect_agents/run.py†L16-L25〗 〖F:src/inspect_agents/run.py†L40-L55〗
**Conclusion**: Recommendation implemented (opt‑in tuple propagation/raise mode); no breaking change to existing callers.

</details>

Follow-ups Post-Implementation — Open Questions

1) Flag Precedence when both flags are True

- Problem
  - Callers may pass both `return_limit_error=True` and `raise_on_limit=True`. We need a clear, documented precedence rule to avoid ambiguity.
- Current Behavior (code today)
  - Raising takes precedence: when a tuple is returned and `err is not None`, `run_agent` re-raises `err` before considering the return-tuple path. 〖F:src/inspect_agents/run.py†L44-L55〗
- Options
  - A) Keep “raise wins” (current). Pros: simplest mental model; control-flow via exceptions is explicit. Cons: callers cannot simultaneously inspect the tuple and raise.
  - B) “Return wins” — always return `(state, err)` when `return_limit_error=True`, even if `raise_on_limit=True`. Pros: easier tuple-based branching. Cons: silent override of a strong signal (raise), surprising when both are set.
  - C) Treat as configuration conflict: raise `ValueError` if both flags are True. Pros: forces explicit intent. Cons: breaks currently valid calls that set both.
- Decision Needed
  - Choose and document the precedence rule; propose to keep Option A (“raise wins”) and document it in the guide and signature docstring. 〖F:docs/guides/supervisor-limits.md†L34-L52〗

2) Return Type Shape when `return_limit_error=True` but no tuple upstream

- Problem
  - When `limits` is empty or when no error occurred, Inspect may return a bare `state` (not a tuple). Should `run_agent(..., return_limit_error=True)` force a `(state, None)` shape for type stability, or preserve the upstream shape and return just `state`?
- Current Behavior (code today)
  - Dynamic shape: we only return `(state, err)` when upstream returned a tuple; otherwise we return `state`. 〖F:src/inspect_agents/run.py†L40-L57〗
- Options
  - A) Preserve upstream shape (current). Pros: zero surprise for existing callers; no unconditional tuple creation. Cons: tuple-aware callers must branch on type.
  - B) Force tuple when `return_limit_error=True` — always return `(state, None)` if no error/tuple upstream. Pros: stable type; easier to pattern-match. Cons: subtle API change vs Inspect’s shape; risks breaking implicit assumptions in existing code/tests.
  - C) Add `always_tuple: bool = False` for explicit opt-in to Option B. Pros: flexible; Cons: adds another knob.
- Decision Needed
  - Pick A (status quo) or B (stable tuple) and document with examples; if B, add tests asserting `(state, None)` when no error.

3) Error Type Scope for `raise_on_limit`

- Problem
  - Upstream contract says the second element is `LimitExceededError|None` when `catch_errors=True`. Should we defensively restrict raising to `LimitExceededError` instances, or raise any non-None `err` for forward compatibility?
- Current Behavior (code today)
  - Re-raises whatever object is returned in `err` when non-None (no isinstance guard). 〖F:src/inspect_agents/run.py†L44-L48〗
- Options
  - A) Raise any non-None `err` (current). Pros: forwards-compatible; preserves type/traceback. Cons: could surface unexpected types if upstream changes.
  - B) Restrict to `LimitExceededError`; otherwise wrap in `RuntimeError` with context. Pros: narrows API to the intended class; Cons: hides concrete types if upstream broadens contract.
  - C) Add `strict_limit_error: bool = False` to guard with isinstance when True. Pros: opt-in strictness; Cons: more surface area.
- Decision Needed
  - Document current behavior (A) and decide if stricter guard is required before a stable upstream contract is pinned.

Acceptance Criteria (for closing these questions)

- Tests
  - Precedence: add a test where both flags are True and a limit is exceeded; assert that an exception is raised and the tuple path is not taken.
  - Shape: add a test with `return_limit_error=True` and `limits=[]`; decide expected return (`state` vs `(state, None)`) and assert accordingly.
  - Type scope: if choosing B/C, add tests stubbing a non-`LimitExceededError` `err` and assert the chosen behavior (raise as-is vs wrap vs guard).
- Docs
  - Update `supervisor-limits.md` examples to note precedence and return shape explicitly. 〖F:docs/guides/supervisor-limits.md†L34-L52〗
- Code
  - If decisions imply behavior changes, update `run_agent` with minimal, well-documented adjustments and keep defaults backward compatible. 〖F:src/inspect_agents/run.py†L11-L25〗

---

# Iterative Agent — Limits and Pruning (max_messages, env fallbacks)

Date: 2025-09-04

Context

- We introduced a message-based pruning cap `max_messages` to the iterative agent and gave it higher precedence than the previous heuristic (keep last `2*max_turns`). This enables predictable memory use across provider/tool burstiness. Code changes live in the iterative agent and wrapper.
- We also added environment fallbacks for loop limits: when args are `None`, read `INSPECT_ITERATIVE_TIME_LIMIT` (seconds) and `INSPECT_ITERATIVE_MAX_STEPS` before the loop starts.
- Unit tests cover both behaviors: `max_messages` tail precedence and env-driven `max_steps`/time normalization.

Decisions

1) Tail vs global cap for `max_messages`
- Decision: Keep tail-only semantics; preserve the first system and first user messages (prefix), then apply `max_messages` to the remaining tail. Rationale: retains crucial seed context and predictable recent history.

2) Minimum bound for `max_messages`
- Decision: No hard clamp; emit a warning when `max_messages` < 6 and document suggested ranges. Rationale: avoid hidden behavior while nudging away from pathological settings.

3) Env fallback normalization
- Decision: Normalize env values `<= 0` for `INSPECT_ITERATIVE_TIME_LIMIT` and `INSPECT_ITERATIVE_MAX_STEPS` to unset (`None`). Explicit arguments still accept `0` as-is if passed directly. Rationale: treat `0` in env as likely misconfiguration; keep explicit code paths precise.

References
- Implementation: iterative pruning and env fallbacks in `src/inspect_agents/iterative.py`; wrapper pass-through in `src/inspect_agents/agents.py`.
- Tests: `tests/inspect_agents/test_iterative_limits.py` covers tail precedence, env-driven steps, time normalization, and warning emission.

---

# Iterative Agent — Pruning Env Toggles + Debug Log

Date: 2025-09-04

Context

- Goal: Make pruning behavior configurable via env and observable via a concise log line when pruning occurs.
- Code: Implementation lives in `src/inspect_agents/iterative.py` within the iterative loop. Effective values are computed once per run:
  - `_eff_prune_after`: threshold for opportunistic prune; sourced from the function arg or `INSPECT_PRUNE_AFTER_MESSAGES` when the arg is `None` or at the default `120`.
  - `_eff_prune_keep`: keep window; sourced from the function arg or `INSPECT_PRUNE_KEEP_LAST` when the arg is at the default `40`.
  - `_prune_debug`: debug toggle enabled if `INSPECT_PRUNE_DEBUG` or `INSPECT_MODEL_DEBUG` is set (reuses the existing model debug convention).
- Behavior:
  - If `_eff_prune_after` is set and `len(state.messages)` exceeds it, prune with `prune_messages(..., keep_last=_eff_prune_keep)` and emit a single `logger.info` line.
  - On length overflow handling (e.g., provider stop_reason=`model_length`), prune immediately using `_eff_prune_keep` and emit a single `logger.info` line.
  - Non‑positive values from env: `INSPECT_PRUNE_AFTER_MESSAGES<=0` disables threshold pruning; `INSPECT_PRUNE_KEEP_LAST` is clamped to `>=0`.

Open Question 1 — Debug Toggle Semantics

- Problem
  - Should pruning logs be gated by a dedicated toggle or reuse the existing model debug toggle? Operators may prefer a narrowly scoped switch.
- Current Behavior
  - Enabled if either `INSPECT_PRUNE_DEBUG` or `INSPECT_MODEL_DEBUG` is set.
- Options
  - A) Keep current (either toggle enables). Pros: convenient, aligns with model debug; Cons: enabling model debug turns on pruning logs too.
  - B) Require only `INSPECT_PRUNE_DEBUG` (ignore `INSPECT_MODEL_DEBUG`). Pros: precise control; Cons: less convenient.
  - C) Make reuse configurable (e.g., `INSPECT_PRUNE_DEBUG_INHERIT=1`). Pros: explicit; Cons: more knobs.
- Decision Needed
  - Which toggle policy do we standardize on for production?

<details>
<summary>✅ Answer Found in Implementation</summary>

**Finding**: Debug logs enable when either `INSPECT_PRUNE_DEBUG` or `INSPECT_MODEL_DEBUG` is set.
**Evidence**: `_prune_debug` computed as `bool(os.getenv("INSPECT_PRUNE_DEBUG") or os.getenv("INSPECT_MODEL_DEBUG"))`. 〖F:src/inspect_agents/iterative.py†L178-L182〗
**Conclusion**: Option A (either toggle enables) is implemented; reflects reuse of the existing model debug convention.

</details>

Open Question 2 — Env Override Precedence When Args Equal Defaults

- Problem
  - Env overrides currently apply when callers pass `None` or the literal defaults (`prune_after_messages=120`, `prune_keep_last=40`). A caller who intentionally passes `120`/`40` might be surprised if env values take precedence.
- Current Behavior
  - Treat “equal to default” as equivalent to “unset” for purposes of env override.
- Options
  - A) Status quo (env can override default‑like args). Pros: operators win; Cons: may surprise explicit callers.
  - B) Env only when arg is `None`. Pros: no ambiguity; Cons: operators cannot override default‑like args without code change.
  - C) Add a sentinel arg (e.g., `prune_after_messages="env"`) to force env, otherwise literal numbers always win. Pros: explicit intent; Cons: API quirk.
- Decision Needed
  - Do we keep status quo or switch to “env only when None”?

<details>
<summary>✅ Answer Found in Implementation</summary>

**Finding**: Env overrides apply when args are `None` or equal to the documented defaults (`120` for threshold; `40` for keep window).
**Evidence**: Threshold override if `prune_after_messages is None or == 120`; keep window override if `prune_keep_last == 40`. 〖F:src/inspect_agents/iterative.py†L157-L165〗 〖F:src/inspect_agents/iterative.py†L168-L175〗
**Conclusion**: Option A (status quo: env can override default‑like args) is implemented.

</details>

Open Question 3 — Zero/Negative Semantics for Threshold

- Problem
  - Interpreting `INSPECT_PRUNE_AFTER_MESSAGES=0` as immediate prune would prune every step; interpreting it as “disabled” avoids pathological behavior but must be documented.
- Current Behavior
  - `<=0` from env disables threshold prune (`_eff_prune_after=None`). Overflow‑driven prune still applies.
- Options
  - A) Keep “non‑positive disables”.
  - B) Treat `0` as “immediate prune” (not recommended) and `<0` as disable.
- Decision Needed
  - Confirm “non‑positive disables” as the contract and document it in user‑facing docs.

<details>
<summary>✅ Answer Found in Implementation</summary>

**Finding**: Non‑positive env values disable threshold pruning; overflow‑driven prune still applies.
**Evidence**: `_eff_prune_after = v if v > 0 else None` during env override resolution. 〖F:src/inspect_agents/iterative.py†L160-L164〗
**Conclusion**: Option A (“non‑positive disables”) is implemented.

</details>

Open Question 4 — Log Format and Prefix

- Problem
  - Operators want grep‑able, stable logs; we need to finalize the format and prefix.
- Current Behavior
  - `logger.info("Prune: reason=<threshold|overflow> pre=%d post=%d keep_last=%d [threshold=%s]")`.
- Options
  - A) Keep as-is; rely on the leading `Prune:` marker.
  - B) Prefix with component: `iterative.prune: ...` for easier filtering.
  - C) Add step number and/or state id for correlation (e.g., `step=<n>`).
  - D) Emit structured JSON (logfmt/JSON) — heavier change, may conflict with existing logging config.
- Decision Needed
  - Choose prefix and whether to include `step` (and any additional fields) now.

<details>
<summary>✅ Answer Found in Implementation</summary>

**Finding**: Current log format uses the `Prune:` prefix without a `step` field.
**Evidence**: Threshold log: `"Prune: reason=threshold pre=%d post=%d keep_last=%d threshold=%s"`; overflow log: `"Prune: reason=overflow pre=%d post=%d keep_last=%d"`. 〖F:src/inspect_agents/iterative.py†L309-L314〗 〖F:src/inspect_agents/iterative.py†L360-L364〗
**Conclusion**: Option A (“keep as‑is; rely on `Prune:` marker”) appears to be the implemented choice.

</details>

Acceptance Criteria (for closure)

 - Written policy for toggle precedence and env override rules is reflected in README/docs.
 - Unit tests assert the chosen semantics (env override behavior and log format fields).
 - Example logs in docs match the finalized format, including the chosen prefix.

---

# Sandbox Preflight — Open Questions

Date: 2025-09-04

Context

- We introduced env‑controlled sandbox preflight in `inspect_agents.tools_files`:
  - `INSPECT_SANDBOX_PREFLIGHT=auto|skip|force` (default `auto`).
  - `INSPECT_SANDBOX_PREFLIGHT_TTL_SEC` (default `300` seconds; `0` disables caching).
  - `INSPECT_SANDBOX_LOG_PATHS=1` to enrich the warn log with `fs_root` and `sandbox_tool`.
- Defaults retain prior behavior: auto + cache, warn‑once on failure, graceful fallback to store.
- New API: `reset_sandbox_preflight_cache()` clears `_SANDBOX_READY/_SANDBOX_WARN/_SANDBOX_TS` for deterministic tests and operator resets.

Why this matters

- Operators and CI can now explicitly choose: force sandbox (no fallback), skip checks for determinism, or auto with caching for performance.
- TTL + reset enable predictable rechecks without process restarts; enriched warnings aid debugging by surfacing `fs_root` and tool context when desired.

Open Question 1 — Exception Type for Force Mode

- Problem
  - In `force` mode, preflight failures currently raise `ToolException` (from `inspect_tool_support` when available, else a local fallback). This blends preflight failure with general tool errors.
- Options
  - A) Keep `ToolException` for compatibility; rely on error strings and `files:sandbox_preflight` warn to diagnose.
  - B) Introduce a dedicated `SandboxPreflightError` (new type) for clearer handling and testability; wrap underlying details.
  - C) Use a subtype of `ToolException` (e.g., `ToolException("SandboxPreflightError: ...")`) to preserve catch‑all semantics with a discriminant prefix.
- Considerations
  - API stability in existing tests and integrations that catch `ToolException`.
  - Need for programmatic branching on preflight errors versus runtime tool errors.
- Decision Needed
  - Choose error strategy (A/B/C). If B/C, document in reference and add tests asserting exception type and message contract.

Open Question 2 — Default TTL Value

- Problem
  - TTL defaults to `300s`. For local dev, shorter TTL (e.g., `60s`) might reduce confusion when the environment changes; for CI, longer TTL reduces repeated checks.
- Options
  - A) Keep `300s` universally (current).
  - B) Use mode‑aware defaults: `CI=1` → `300s`, otherwise `60s`.
  - C) Keep `300s` but document `TTL=0` for always‑recheck during debugging.
- Considerations
  - Consistency across environments vs ergonomics for iterative dev.
  - Overhead of frequent checks in large runs.
- Decision Needed
  - Pick a default policy; if B, implement conditional defaulting keyed off `CI` and document precedence.

Open Question 3 — Logging Scope and Levels

- Problem
  - Today we log a warn‑level `tool_event` only on failure (`files:sandbox_preflight`). When `INSPECT_SANDBOX_LOG_PATHS=1`, we include `fs_root` and `sandbox_tool`. There is no success/info log.
- Options
  - A) Keep warn‑only to minimize log noise (current).
  - B) Add a one‑time `phase="info"` success event when preflight passes, gated by `INSPECT_SANDBOX_LOG_PATHS=1`.
  - C) Emit success logs only when `INSPECT_LOG_LEVEL=DEBUG` (or similar) to avoid clutter in production.
- Considerations
  - Operator expectations for “positive confirmation” in audits.
  - Backwards compatibility of log parsing and alerting rules.
- Decision Needed
  - Choose A/B/C and update docs/tests accordingly; if adding success logs, define payload fields and one‑time emission semantics.

Related Artifacts

- Implementation: `src/inspect_agents/tools_files.py` (`_ensure_sandbox_ready`, TTL cache, reset API).
- Docs: `docs/how-to/filesystem.md` (preflight usage) and `docs/reference/environment.md` (new envs).
- Tests: `tests/unit/inspect_agents/test_sandbox_preflight_modes.py` (skip/force/TTL/reset/logging).

Next Steps

1) Decide exception strategy for `force` mode and update code/docs/tests.
2) Confirm TTL default policy; consider `CI`‑aware defaulting.
3) Decide whether to add a success/info log and its gating conditions.
4) If a new exception type is introduced, add a migration note and example catch blocks in the how‑to.

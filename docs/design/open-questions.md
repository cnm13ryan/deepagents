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

Detailed Open Questions — Transcript “Skipped” ToolEvents

1) Error code strategy (type vs mapping vs docs)
- Context: ADR 0005 specifies `error.code="skipped"` for skipped calls; Inspect’s ToolCallError currently does not define a `"skipped"` variant. We emit `ToolCallError("approval", "Skipped due to handoff")` and attach attribution via metadata. 〖F:docs/adr/0005-tool-parallelism-policy.md†L22-L25〗 〖F:external/inspect_ai/src/inspect_ai/tool/_tool_call.py†L61-L74〗 〖F:src/inspect_agents/approval.py†L282-L303〗
- Options:
  - Upstream type: add `"skipped"` to Inspect’s `ToolCallError` union; update producers/consumers and tests. Pros: explicit, easy to query. Cons: upstream change and compatibility churn.
  - Export-time mapping: keep `type="approval"` in transcripts; when exporting logs, map events where `metadata.source=="policy/handoff_exclusive"` to `{code:"skipped", message:...}` for JSON consumers. Pros: minimal blast radius now. Cons: in-memory vs exported semantics differ. Candidate hook: `write_transcript()` serialization. 〖F:src/inspect_agents/logging.py†L32-L38〗 〖F:src/inspect_agents/logging.py†L41-L60〗
  - Docs-only: document `type="approval"` as the canonical representation for policy-driven skips; require consumers to key off `metadata.source` and `selected_handoff_id` rather than a new code.
- Proposal: adopt export-time mapping immediately for operator logs; pursue upstream addition in parallel if broader ecosystem wants `"skipped"` as first-class.

2) Event contract stability (pending, metadata)
- Context: Policy synthesizes `ToolEvent` with `pending=False` and metadata: `selected_handoff_id`, `skipped_function`, and `source:"policy/handoff_exclusive"`. Tests assert this shape. 〖F:src/inspect_agents/approval.py†L291-L303〗 〖F:tests/integration/inspect_agents/test_handoff_exclusive_end_to_end.py†L78-L100〗
- Decision to confirm: treat the following as stable for v1
  - `pending=False` always set on synthesized skip events.
  - `metadata` must include `selected_handoff_id`, `skipped_function`, `source`.
- Rationale: explicit pending state avoids ambiguity; stable metadata keys support analytics and cross-run correlation.

3) message_id timing (now vs v2 executor pre-scan)
- Context: `ToolEvent.message_id` links to a `ChatMessageTool` when one exists. For policy-synthesized skips, no conversation message is added by design; in executor pre-scan (v2) there will also be no `ChatMessageTool` for skipped calls. 〖F:external/inspect_ai/src/inspect_ai/log/_transcript.py†L242-L244〗 〖F:docs/adr/0005-tool-parallelism-policy.md†L22-L25〗
- Options:
  - Defer: keep `message_id=None` for policy-synthesized skips in v1; revisit when implementing v2 pre-scan to decide if a synthetic, trace-only id adds value.
  - Add now: populate `message_id` with the selected handoff’s message id to aid joins. Risk: could imply a 1:1 relation that doesn’t exist; skipped calls have no ChatMessageTool.
- Recommendation: defer; document `message_id` as optional and typically absent for skip events in v1.

---

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

Acceptance Criteria (for closure)

- Written policy for toggle precedence and env override rules is reflected in README/docs.
- Unit tests assert the chosen semantics (env override behavior and log format fields).
- Example logs in docs match the finalized format, including the chosen prefix.

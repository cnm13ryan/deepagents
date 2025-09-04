# TODO: Per‑Message Token Truncation (Token‑Aware Overflow Control)

Status: DONE (2025-09-04)
- Implemented helpers and wiring:
  - `truncate_message_tokens` and `truncate_conversation_tokens` in `src/inspect_agents/_conversation.py`.
  - Iterative agent integrates token-aware truncation on threshold/overflow paths, env‑gated via `INSPECT_PER_MSG_TOKEN_CAP`.
- Tests: `tests/unit/inspect_agents/iterative/test_per_message_truncation.py` and `tests/integration/inspect_agents/test_per_message_token_truncation.py` validate behavior.

## Context & Motivation
- Purpose: Prevent individual oversized messages from blowing context windows by trimming them intelligently.
- Problem: Current pruning is list‑length based (system + first user + tail) and doesn’t shrink giant messages.
- Value: Stabilizes long runs; reduces hard failures on provider length errors.
- Constraints: Provider‑agnostic; optional dependency on `tiktoken`; keep default off.

## Implementation Guidance
- Examine:
  - `src/inspect_agents/iterative.py` — overflow handler after `model_length` or `IndexError`.
  - `src/inspect_agents/_conversation.py` — add token‑aware helpers while preserving existing list‑length prune.
- Grep:
  - `_OVERFLOW_HINT`, `prune_messages(`, `model_length`, `IndexError`.
- Steps:
  1) Add helpers to `_conversation.py`:
     - `truncate_message_tokens(msg, max_tokens, tokenizer)` — trim text/reasoning fields proportionally.
     - `truncate_conversation_tokens(msgs, max_tokens_per_msg, encoding="o200k_base")` — apply to a window of recent messages, skip tool images, preserve roles.
  2) In `iterative.py` overflow block:
     - Append `_OVERFLOW_HINT` to user, then call token‑aware truncation (when enabled) before length‑based prune.
  3) Configuration:
     - Env: `INSPECT_PER_MSG_TOKEN_CAP=190000` (default None = disabled).
     - Optional arg on `build_iterative_agent(max_tokens_per_msg: int | None = None)`.
  4) Fallback behavior: if `tiktoken` unavailable or cap unset, skip token truncation and use current length prune.

## Scope Definition
- Apply in iterative agent only; do not change submit‑style supervisor.
- Keep feature behind env/arg; default remains current behavior.

## Success Criteria
- Behavior: When enabled, an overlong message is truncated (add a short suffix like `...[+X tokens trimmed]`) and the loop continues.
- Tests: Unit tests for helper functions and overflow path; ensure tool messages remain paired with their assistant parents.
- Performance: Truncate only a tail window (e.g., last 200 messages) to bound cost.

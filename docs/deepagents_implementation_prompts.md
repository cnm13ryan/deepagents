# DeepAgents Implementation Prompts

## 5.1 Context Quarantine Implementation (via Filters + StoreModel)

### Context & Motivation

- **Purpose:** Implement message-context isolation for sub-agents to replicate the original deepagents' *context quarantine*, ensuring that sub-agents cannot see or modify the supervisor's conversation history except through shared state (todos and files).
- **Impact:** Prevents prompt injection between supervisor and sub-agents, enabling safe delegation. Aligns the rewrite with original design principles and improves security.
- **Dependencies:** Use Inspect's `handoff()` `input_filter`/`output_filter` to control visibility and StoreModel‑backed `Todos`/`Files` for shared state. No unified state replacement for Inspect's `AgentState` is needed.
- **Priority:** Critical.

### Current State Analysis

- **Issue Description:** In the Inspect rewrite, sub‑agents created by `build_subagents` currently inherit the caller's history (subject to Inspect defaults). We don't set explicit filters, so quarantine is not enforced.
- **Reproduction Steps:**

```python
# In a Python REPL or test
from inspect_agents.agents import build_supervisor, build_subagents, BASE_PROMPT
# Create supervisor with a simple prompt and a dummy tool
sup = build_supervisor("Test supervisor", tools=[])
# Create a sub-agent
sub_cfg = {"name": "child", "description": "Test", "prompt": "Sub prompt", "tools": []}
sub = build_subagents([sub_cfg], base_tools=[])[0]
state = {}
# Run supervisor: messages added
_ = await sup(state)
# Run sub-agent: shares same messages list
_ = await sub(state)
print(state)  # shows both supervisor and sub-agent messages intertwined
```

*Expected:* Supervisor and sub-agent should maintain separate message histories except for shared todos and files.

- **Affected Files:** `agents.py` (build_subagents), possibly `state.py` for new state classes.
- **Error Logs:** No explicit errors; the defect is behavioural.

### Implementation Guide

- **Key Files to Examine:**
  - `src/inspect_agents/agents.py` – `build_subagents` (set default `input_filter`/`output_filter`).
  - `src/inspect_agents/state.py` – `Todos` and `Files` StoreModels (shared state remains here).
  - `external/inspect_ai/agent/_filter.py` – built‑ins: `content_only`, `remove_tools`, `last_message`.
  - `external/inspect_ai/model/_call_tools.py` – `agent_handoff()` behavior.

### Default Policy and Rationale

- Strict quarantine (default): Each sub‑agent starts with no prior message history. Compose filters `remove_tools` → `content_only` → `last_message` so the sub‑agent only sees the immediate boundary message (and never system/tool context). This mirrors the original “context quarantine,” minimizes prompt‑injection risk, and makes behaviour easier to reason about.
- Scoped quarantine (optional): Retain only the last user task plus an optional summary of shared `Todos`/`Files` to improve local context. This carries slightly higher leakage risk; keep it opt‑in and clearly marked in config.
- Inheritance: Nested handoffs inherit the parent’s quarantine by default so every level enjoys the same isolation guarantees. Allow per‑sub‑agent overrides to relax or change the filter when debugging or when a specific sub‑agent needs more context.

#### Scoped Summary Payload (opt‑in)

When `scoped` quarantine is enabled, append a small, machine‑friendly JSON summary after the boundary message so the sub‑agent can see the immediate objective and shared state without calling tools:

```
{
  "version": "v1",
  "scope": "scoped",
  "todos": [
    {"content": "…", "status": "pending"},
    {"content": "…", "status": "in_progress"}
  ],
  "files": {
    "list": ["README.md", "src/app.py", "tests/test_app.py"],
    "remaining_count": 12
  }
}
```

Constraints:
- Cap size (e.g., ≤ 2 KB); at most N=10 todos and M=20 filenames; never include file contents.
- Keep it as a separate user message appended by the filter; do not use system messages (Inspect removes them during handoff).

- **Search Patterns:**
```bash
grep -R "class Todos" src/inspect_agents
grep -R "state.messages" src/inspect_agents
```

- **Reference Implementation (Inspect‑native):** Use `handoff(agent, input_filter=..., output_filter=...)`. For strict quarantine, compose filters that remove tools and system messages and reduce context to the most recent boundary (e.g., `remove_tools` → `content_only` → `last_message`). Keep `output_filter=content_only` so returned messages are safe.
- **Integration Points:** In `build_subagents`, when `input_filter`/`output_filter` aren’t provided, apply a strict default as above. Continue using StoreModels (`Todos`, `Files`) for shared state; do not clone messages.

### Implementation Scope

**In Scope:**
- [ ] Provide quarantine filters: `strict_quarantine_filter()` and optionally `scoped_quarantine_filter(k)` built on Inspect primitives.
- [ ] Default `build_subagents` to use strict input filtering when none is supplied; keep `output_filter=content_only`.
- [ ] Tests to ensure sub‑agent input history is filtered (no tools/system; bounded context) and supervisor history only receives filtered output.
- [ ] Ensure nested handoffs inherit the active input filter unless explicitly overridden in that sub‑agent’s config.

#### Repo‑wide Toggles (debug/ops)

Provide repo‑wide environment flags with per‑agent override precedence:

- `INSPECT_QUARANTINE_MODE`: `strict` (default) | `scoped` | `off`
  - `strict`: compose `remove_tools` → `content_only` → `last_message`.
  - `scoped`: strict + append JSON summary (above).
  - `off`: identity filter (use only for debugging).
- `INSPECT_QUARANTINE_INHERIT`: `1` (default) | `0`
  - `1`: apply the active input filter to nested handoffs by default.
  - `0`: do not inherit; nested handoffs must opt‑in or specify their own filter.

Precedence: explicit `input_filter`/`output_filter` in a sub‑agent config ALWAYS wins over env flags.

#### Per‑Agent Configuration (experimental)

Expose a minimal, declarative surface in `SubAgentCfg` for common cases while keeping advanced customisation in code:

- `mode`: `handoff` (default) | `tool`
- `context_scope`: `strict` (default) | `scoped`
- `include_state_summary`: boolean (defaults to true when `context_scope=scoped`)

Notes:
- Mark as experimental initially; treat as sugar over explicit `input_filter`/`output_filter` to avoid locking the API too early.
- Precedence: explicit filters in a sub‑agent config override `context_scope`.
- Global env flags still apply when `context_scope` is not set.

Example YAML:

```yaml
subagents:
  - name: researcher
    description: Investigate a topic with web browsing
    prompt: "Research and summarise findings."
    mode: handoff
    context_scope: scoped  # experimental
    include_state_summary: true
    tools: [web_search, ls, read_file]
```

**Out of Scope:**
- [ ] Changes to Inspect core library.
- [ ] Streaming or LangChain Studio integration.
- [ ] New tools beyond those required for state cloning.

### Testing Protocol

#### Pre-Implementation Tests

```bash
# Verify that, without default filters, sub‑agent sees unfiltered history
pytest tests/test_context_isolation.py::test_subagent_sees_unfiltered_history -v
# Expected: FAIL before defaults are added
```

#### Progressive Validation

```bash
# Step 1: Unit tests for state cloning
pytest tests/unit/test_state_cloning.py -v

# Step 2: Integration test with supervisor and sub-agent
pytest tests/integration/test_context_isolation.py -v

# Step 3: Regression testing
pytest --maxfail=1 --disable-warnings -q

# Step 4: Coverage verification
pytest --cov=inspect_agents --cov-report=term-missing
```

#### Edge Cases

- [ ] Sub‑agent modifies files and todos; verify shared StoreModel visibility.
- [ ] Very long parent history; filters maintain bounded context and remove tools/system.
- [ ] Nested sub‑agents; confirm filters apply at each handoff.

### Success Criteria

- [ ] Tests in `tests/test_context_isolation.py` pass.
- [ ] No existing tests regress.
- [ ] Coverage does not decrease.
- [ ] Documentation updated to describe context quarantine.
- [ ] Example usage updated.

### Quick Start

```bash
git checkout -b feature/quarantine-filters && rg -n "build_subagents\(|handoff\(" src/inspect_agents external/inspect_ai/src
```

## 5.2 StoreModel + Filters (No Unified State)

### Context & Motivation

- **Purpose:** Keep conversation in Inspect’s `AgentState`; use `Todos`/`Files` StoreModels for shared persistence and `input_filter`/`output_filter` for quarantine. Do not attempt to replace `AgentState`.
- **Impact:** Aligns with Inspect APIs; reduces complexity and brittleness; enables quarantine using supported mechanisms.
- **Priority:** High (supersedes prior unified‑state plan).

### Current State Analysis

- **Observation:** `Todos`/`Files` already use `StoreModel`; messages live in `AgentState`. Inspect does not accept a custom state object for `react()`/agents.
- **Affected Files:** `state.py` (no change), `agents.py` (filter defaults), `migration.py` (remove `state_schema` references from docs/comments).

### Implementation Guide

- Keep `Todos`/`Files` as StoreModels; add helpers where useful (see 5.3).
- Do not create a unified state or `Messages` StoreModel.
- Remove/ignore any `state_schema` argument in docs/examples.

<!-- No unified state or DeepAgentState: conversation stays in Inspect AgentState; use StoreModels + filters. -->

### Implementation Scope

**In Scope:**
- [ ] Excise unified‑state references from docs.
- [ ] Add unit tests that cover StoreModel read/write during sub‑agent runs.

**Out of Scope:**
- Rewriting Inspect’s `AgentState` or message storage.

### Testing Protocol

#### Pre-Implementation Tests

```bash
pytest tests/test_docs_and_configs.py::test_no_unified_state_mentions -v
```

#### Progressive Validation

```bash
pytest tests/unit/test_storemodels.py -v
pytest tests/integration/test_quarantine_filters.py -v
pytest --maxfail=1 -q
pytest --cov=inspect_agents --cov-report=term-missing
```

#### Edge Cases

- [ ] Very large histories; filters keep bounded view.
- [ ] Concurrent StoreModel updates; document last‑write semantics.
- [ ] Validation errors handled by Pydantic.

### Success Criteria

- [ ] New tests pass; StoreModel read/write and filter behavior verified.
- [ ] No regression in existing tests.
- [ ] Documentation updated.
- [ ] Example updated.

### Quick Start

```bash
git checkout -b chore/remove-unified-state-docs && rg -n "state_schema|DeepAgentState|unified state" -S
```

## 5.3 Todo Status Transitions

### Context & Motivation

- **Purpose:** Implement automatic status transitions for todo items and provide helper functions for agents to mark todos as `pending`, `in_progress` and `completed`. Aligns behaviour with the original deepagents, which updates todo statuses as tasks are started and completed.
- **Impact:** Enhances the planning tool by enabling progress tracking; improves user feedback and sub-agent coordination.
- **Dependencies:** None (uses existing `Todos` StoreModel). May interact with context quarantine (5.1) if status updates occur inside sub‑agents.
- **Priority:** Medium.

### Current State Analysis

- **Issue Description:** The Inspect rewrite stores todos via `Todos` but does not provide explicit methods or reducer functions to change statuses based on agent actions. Agents must manually update the list; there is no enforcement of valid transitions.
- **Reproduction Steps:**

```python
from inspect_agents.tools import write_todos
todos_tool = write_todos()
state = {}
await todos_tool.func(todos=[{"content": "Task 1", "status": "pending"}], state=state)
# no helper to mark a todo as in_progress or completed
```

- **Affected Files:** `tools.py`, potential new module for reducers.
- **Error Logs:** None.

### Implementation Guide

- **Key Files to Examine:**
  - `src/inspect_agents/tools.py` – implementation of `write_todos`
  - `src/inspect_agents/state.py` – `Todos` model

- **Search Patterns:**
```bash
grep -R "status" src/inspect_agents/tools.py
```

- **Reference Implementation:** The original deepagents uses reducer functions to update todo statuses and ensures statuses reflect progress.
- **Integration Points:** Implement a helper tool `update_todo_status` or extend `write_todos` to allow updating statuses. Alternatively, provide a reducer function that examines tool calls and updates statuses when a `task` starts or completes.

### Implementation Scope

**In Scope:**
- [ ] Add an Inspect tool `update_todo_status(todo_index: int, status: str)` or modify `write_todos` to support updating existing items by index.
- [ ] Update `Todos` model with a method `update_status(index, status)` that validates transitions.
- [ ] Write unit tests for valid and invalid transitions (e.g., cannot move directly from pending to completed without in_progress).

**Out of Scope:**
- [ ] UI or CLI changes to display status progress.
- [ ] Synchronisation across distributed processes.

### Testing Protocol

#### Pre-Implementation Tests

```bash
pytest tests/test_todo_status.py::test_missing_status_helpers -v
# Expected: FAIL
```

#### Progressive Validation

```bash
pytest tests/unit/test_todo_status.py -v
pytest tests/integration/test_todo_flow.py -v
pytest --maxfail=1 -q
pytest --cov=inspect_agents --cov-report=term-missing
```

#### Edge Cases

- [ ] Invalid index; should raise an error.
- [ ] Invalid status value; should be rejected.
- [ ] Concurrent updates from multiple sub-agents.

### Success Criteria

- [ ] New tests pass; todo statuses can be updated correctly.
- [ ] No regression in existing tests.
- [ ] Documentation and examples updated.

### Quick Start

```bash
git checkout -b feature/todo-status && grep -R "write_todos(" src/inspect_agents
```

## 5.4 Detailed Prompt Parity

### Context & Motivation

- **Purpose:** Restore missing guidelines and instructions from the original deepagents base prompt (e.g., warnings against hallucinating file contents, instructions on context quarantine, proper usage of the planning tool, and when to delegate tasks). Ensures that the agent receives the same behavioural cues as the original.
- **Impact:** Improves agent reliability and user trust; reduces the likelihood of misuse of tools.
- **Dependencies:** None.
- **Priority:** Medium (Low effort).

### Current State Analysis

- **Issue Description:** The Inspect rewrite's `BASE_PROMPT` includes Todo and file-system sections and enumerates optional tools. However, instructions present in LangGraph deepagents (e.g., context quarantine guidelines, memory guidelines) are missing.
- **Affected Files:** `agents.py`.

### Implementation Guide

- **Key Files to Examine:**
  - `src/inspect_agents/agents.py` – `BASE_PROMPT` constant and `build_supervisor`
  - deepagents original prompts (available in the original repository or deepwiki)

- **Integration Points:** Update `BASE_PROMPT` to include missing instructions. Add guidance on context quarantine (once implemented) and memory usage. Ensure the prompt remains concise and fits within model token limits.

### Implementation Scope

**In Scope:**
- [ ] Identify missing guidelines by reviewing the original deepagents prompt.
- [ ] Update `BASE_PROMPT` accordingly.
- [ ] Add tests that inspect the agent's prompt to ensure required phrases are present.

**Out of Scope:**
- [ ] Redesigning the prompt format.

### Testing Protocol

- [ ] Write a test that asserts `BASE_PROMPT` contains specific strings (e.g., "do not hallucinate file contents").
- [ ] Ensure the new prompt does not exceed a reasonable token limit (maybe 2000 tokens).
- [ ] Regression tests.

### Success Criteria

- [ ] Updated prompt includes all necessary guidelines.
- [ ] Tests verifying prompt contents pass.
- [ ] No regression.

### Quick Start

```bash
git checkout -b feature/prompt-parity && sed -n '1,200p' src/inspect_agents/agents.py
```

## 5.5 Clarify Sub-agent API Semantics

### Context & Motivation

- **Purpose:** Provide documentation and code examples that explain the mapping between the original `task` tool semantics and Inspect's `handoff` and `tool` modes. Ensure developers know when to use each mode and how to configure sub-agents.
- **Impact:** Reduces confusion during migration and encourages correct usage of sub-agents.
- **Dependencies:** None.
- **Priority:** Medium.

### Current State Analysis

- **Issue Description:** In the original framework, `task` returns control to the sub-agent until completion. In Inspect, `build_subagents` can wrap a sub-agent as a *handoff* (control flow) or *tool* (callable once and returns output). The mapping between these options and the original semantics is not documented.
- **Affected Files:** `agents.py`, `config.py`, README.

### Implementation Guide

- **Key Files to Examine:**
  - `src/inspect_agents/agents.py` – `build_subagents` implementation (default filters)
  - README – document when to use `mode="handoff"` vs `mode="tool"`, and how filters apply.

### Mode Selection Guidance

- Use `handoff` for tasks that require iterative reasoning, multi‑step planning, tool chaining, or quarantine. Handoff preserves the richer delegation semantics and supports input/output filters for isolation.
- Use `as_tool` when the sub‑agent is deterministic and effectively stateless (e.g., a summariser, data fetcher, or formatter). It behaves like a function call and reduces overhead; prefer it for narrow, well‑defined operations.
- Rule of thumb: default to `handoff` for broad/uncertain tasks; choose `as_tool` for narrow, predictable ones. Apply strict quarantine to handoffs by default; filters are not generally relevant to `as_tool` due to its single‑shot nature.

- **Integration Points:** Add docstrings and update the repository README to describe when to use `mode="handoff"` versus `mode="tool"`. Provide examples mirroring the original `task` usage.

### Implementation Scope

**In Scope:**
- [ ] Write documentation explaining the differences and mapping.
- [ ] Add type hints or parameter descriptions to `SubAgentCfg` fields (`mode`).
- [ ] Provide example YAML configuration demonstrating both modes.

**Out of Scope:**
- [ ] Changing the implementation of sub-agent modes.

### Testing Protocol

- [ ] Manual review of documentation; optionally write a linter test that ensures `README.md` contains the required section.

### Success Criteria

- [ ] Documentation updated and examples provided.
- [ ] Test or manual review confirms clarity.

### Quick Start

```bash
git checkout -b docs/subagent-modes && grep -R "build_subagents(" src/inspect_agents
```

## Dependency Graph

Below is a high-level dependency graph illustrating how the proposed features interrelate. Arrows indicate that one feature should be implemented before another.

```
Context quarantine (5.1, filters)
│
├──► Todo status transitions (5.3)
│
└──► Detailed prompt parity (5.4) – includes guidance on quarantine behavior

Clarify sub-agent API semantics (5.5) – in parallel; independent of state changes

LangGraph streaming & Studio integration – optional; deferred
```

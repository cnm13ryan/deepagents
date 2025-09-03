# TODO — Canonical Tools Rework (Self‑Contained Implementation Prompts)

Status: Complete
- Completed: 1) Sandbox timeouts; 2) ToolException errors; 3) Typed results (env‑gated);
  4) Unified files tool with wrappers; 5) Approval preset tightening; 6) Structured observability;
  7) `delete_file` command/tool with tests; 8) Strict Pydantic input models for files and todos (`extra="forbid"`).

This document contains discrete, handoff‑ready prompts for improving the canonical tools (`Todos` + virtual FS) and related approval/observability policies. Each prompt is complete and actionable for a professional SWE.

References
- Tools code: `src/inspect_agents/tools.py`
- State models: `src/inspect_agents/state.py`
- Approvals: `src/inspect_agents/approval.py`
- Umbrella & design docs: `docs/tool-umbrellas.md`, `docs/stateless-vs-stateful-tools-harmonized.md`

---

## 1) Add Timeouts to Sandbox Text Editor Calls

**Context & Motivation**
- Purpose: Prevent unbounded waits when file tools proxy to `text_editor` in sandbox FS mode; align with the repo’s timeout guidance.
- Problem: Store‑backed paths use `anyio.fail_after(...)`; sandbox branches do not, so editor RPCs can hang.
- Constraints: Keep default timeout controlled by `INSPECT_AGENTS_TOOL_TIMEOUT` (default 15s).

**Implementation Guidance**
- Files to examine: `src/inspect_agents/tools.py`
- Greppables: `text_editor(`, `anyio.fail_after(`, `_default_tool_timeout`, `_use_sandbox_fs`
- Snippets:
  - `read_file` sandbox path: `editor = text_editor(); raw = await editor(command="view", ...)`
  - `write_file` sandbox path: `await editor(command="create", ...)`
  - `edit_file` sandbox path: `await editor(command="str_replace", ...)`
- Related deps: `anyio` for timeouts; Inspect Tool Support’s in‑process `text_editor`.

**Scope Definition**
- Wrap all sandbox `text_editor(...)` awaits in `anyio.fail_after(_default_tool_timeout())`.
- Do not alter store‑backed branches or return shapes.

**Success Criteria**
- All editor calls in sandbox mode are bounded by the same timeout used elsewhere.
- Tests: Add/extend a unit test that stubs `text_editor` to sleep > timeout and asserts timeout surfaces as a tool error (or exception), without changing successful paths.

---

## 2) Standardize Error Handling With `ToolException`

**Context & Motivation**
- Purpose: Use structured, consistent error handling for user‑fixable issues (missing file, bad offset/status).
- Problem: Tools return error strings (e.g., `"Error: File 'x' not found"`) or JSON text `{ok:false}` instead of raising `ToolException`.
- Background: Vendored Tool Support maps `ToolException` into structured tool errors.

**Implementation Guidance**
- Files to examine: `src/inspect_agents/tools.py`
- Greppables: `return f"Error:`, `json.dumps({"ok": False`, `ToolException`
- Targets:
  - `read_file`: replace not‑found and bad‑offset string returns with `ToolException`.
  - `edit_file`: replace not‑found and missing‑substring string returns with `ToolException`.
  - `update_todo_status`: replace JSON error returns with `ToolException` (keep success pathway unchanged for now).
- Related deps: `external/inspect_ai/.../common_types.py::ToolException`.

**Scope Definition**
- Convert only clearly user‑correctable errors to `ToolException`; keep success outputs intact.
- Avoid changing signatures or happy‑path return types.

**Success Criteria**
- On error, framework emits structured tool errors (ChatMessageTool.error present) instead of error strings.
- Tests: Update/add unit tests to assert `ToolException` mapping; preserve existing happy‑path assertions.

---

## 3) Typed Result Models Behind Env Flag

**Context & Motivation**
- Purpose: Introduce consistent, typed outputs for canonical tools without breaking existing consumers.
- Problem: Mixed return shapes (strings, list[str], JSON string) complicate downstream handling.
- Constraint: Preserve legacy behavior by default.

**Implementation Guidance**
- Files: `src/inspect_agents/tools.py` (or new `src/inspect_agents/results.py` for models)
- Greppables: `name="read_file"`, `name="write_file"`, `name="edit_file"`, `name="ls"`, `name="write_todos"`, `name="update_todo_status"`
- Add Pydantic models, e.g.:
  - `FileReadResult { lines: list[str], summary: str }`
  - `FileWriteResult { path: str, summary: str }`
  - `FileEditResult { path: str, replaced: int|None, summary: str }`
  - `FileListResult { files: list[str] }`
  - `TodoWriteResult { count: int, summary: str }`
  - `TodoStatusResult { index: int, status: str, warning: str|None, summary: str }`
- Env flag: `INSPECT_AGENTS_TYPED_RESULTS=1` → return typed results; otherwise keep legacy strings/lists.

**Scope Definition**
- Implement conditional return of typed models in canonical tools only.
- No parameter or tool name changes in this step.

**Success Criteria**
- With flag enabled, tools return JSON‑serializable typed results; without flag, behavior unchanged.
- Tests: New tests that set the flag and validate shapes; legacy tests continue to pass unmodified.

---

## 4) Unify Files Tools Into One Stateless Tool (Discriminated Union)

**Context & Motivation**
- Purpose: Replace four file tools with a single coherent stateless tool using a discriminated union (`command: "ls"|"read"|"write"|"edit"`).
- Value: Smaller API surface, uniform validation, matches best‑practice template.

**Implementation Guidance**
- New file: `src/inspect_agents/tools_files.py` — unified tool + Pydantic params/results (`extra="forbid"`).
- Integrate: Keep current wrappers in `src/inspect_agents/tools.py` (`ls`, `read_file`, `write_file`, `edit_file`) as thin shims that call the unified tool.
- Greppables: `def ls(`, `def read_file(`, `def write_file(`, `def edit_file(`, `_use_sandbox_fs`, `_default_tool_timeout`
- Reuse existing logic for numbered/truncated lines and sandbox proxying.

**Scope Definition**
- Provide `files_tool()` with union params and typed results; add wrappers for backward compatibility.
- Do not remove legacy tool names yet; mark them deprecated in docstrings.

**Success Criteria**
- New unified tool fully covers functionality; wrappers delegate correctly.
- Tests: New `tests/unit/inspect_agents/test_files_tool_unified.py` covers all commands in store and sandbox modes; verify unknown fields are rejected.

---

## 5) Tighten Approval Presets (Include `python`, Refine Browser Pattern)

**Context & Motivation**
- Purpose: Treat all code execution and browser actions as sensitive in dev/prod approval presets.
- Problem: Current sensitive regex omits `python` and matches browser too broadly.

**Implementation Guidance**
- File: `src/inspect_agents/approval.py`
- Greppables: `sensitive = re.compile`, `approval_preset`, `dev_gate`, `prod_gate`
- Change: `sensitive = re.compile(r"^(write_file|text_editor|bash|python|web_browser_)")`.
- Tests: Extend `tests/integration/inspect_agents/test_approval_chains.py` to include a `python` call and a `web_browser_go` call.

**Scope Definition**
- Update sensitive pattern and keep existing decision logic and redaction.

**Success Criteria**
- Dev preset escalates these tools and rejects via second policy; Prod preset terminates with redacted args.
- Tests assert behavior for `python` and a browser verb.

---

## 6) Add Structured Observability for Tool Calls

**Context & Motivation**
- Purpose: Emit minimal structured logs (start/end/duration, tool name, redacted args) to improve debugging and performance insight.
- Problem: Current logging is sparse (e.g., a warning in `update_todo_status` only); no durations.

**Implementation Guidance**
- Files: `src/inspect_agents/tools.py` (helper + call sites), optionally reuse `redact_arguments` from `src/inspect_agents/approval.py`.
- Greppables: `logging.getLogger(__name__)`, `redact_arguments`, `REDACT_KEYS`
- Add helper: `_log_tool_event(name, phase, args, extra)` using `time.perf_counter()`; redact args and truncate large fields.
- Call before/after key operations in Todos and Files tools.

**Scope Definition**
- Canonical tools only; do not instrument standard tools.
- Keep logs at DEBUG/INFO; avoid logging full file contents.

**Success Criteria**
- Visible start/end log lines with durations and redacted payloads during tests.
- Optional smoke test that asserts redaction (secret absent, `[REDACTED]` present).

---

## 7) Add `delete_file` Capability (Store Mode Only)

**Context & Motivation**
- Purpose: Provide delete operation for parity with `Files.delete_file()` and common workflows.
- Problem: Model supports delete; no tool/verb exists; text editor lacks a delete verb.

**Implementation Guidance**
- Preferred: Add a `delete` command to the unified files tool (`tools_files.py`).
- Shim: Add `def delete_file()` in `src/inspect_agents/tools.py` mirroring others (for back‑compat), calling store path only.
- Sandbox mode: raise `ToolException("delete is disabled in sandbox mode; set INSPECT_AGENTS_FS_MODE=store to delete from the in-memory Files store")` until editor supports it.

**Scope Definition**
- Implement delete for store mode; clear error in sandbox mode.
- Return typed result under typed‑results flag or legacy string otherwise.

**Success Criteria**
- Tests cover: delete success, idempotent delete of missing path (decide: no‑op message vs `ToolException`), sandbox‑mode unsupported error.

---

## 8) Pydantic Input Modeling With `extra="forbid"`

**Context & Motivation**
- Purpose: Strengthen input validation and early typo detection with Pydantic models, per docs.
- Problem: Only `ToolParams/json_schema` are used today; unknown fields may pass quietly.

**Implementation Guidance**
- New file: `src/inspect_agents/tool_types.py` defining Pydantic params for the unified files tool and todo tools. Use `model_config = {"extra": "forbid"}`.
- Integrate: In tool factories, validate incoming args with these models before proceeding (until direct model binding is supported everywhere).
- Greppables: `ToolParams()`, `json_schema(`, `params.properties[...]`

**Scope Definition**
- Introduce Pydantic validation in canonical tools (unified files + todos) without removing `ToolParams` yet.

**Success Criteria**
- Negative test demonstrates unknown field is rejected with a clear error.
- Happy‑path behavior unchanged; legacy wrappers still work.

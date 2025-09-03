# Stateless vs Stateful Tools (Inspect Tool Support)

> Note: This document is superseded by the canonical Harmonized guide. See `../stateless-vs-stateful-tools-harmonized.md` for up‑to‑date definitions, templates, and checklists. This page is retained for historical context.

See also: [Stateless vs Stateful Tools — Harmonized](../stateless-vs-stateful-tools-harmonized.md) for the canonical, consolidated definitions, templates, and checklists that integrate Inspect AI usage patterns.

This guide explains how tools in Inspect Tool Support are categorized as stateless or stateful, and provides concrete design and documentation practices for each. It aligns with the package’s JSON‑RPC + Pydantic patterns, `ToolException` error handling, and `SessionController` for session isolation.

## Definitions

- Stateless tool: A tool that does not retain in‑memory/process state between calls. Each invocation is self‑contained; all required context is provided via parameters. Any persistence (e.g., writing a file) is through external side effects rather than an in‑memory session. Example: the in‑process text editor commands (`view`, `create`, `str_replace`, `insert`, `undo_edit`) operate entirely from parameters and filesystem state, and do not require a session identifier.

- Stateful tool: A tool that maintains per‑session state in memory or via long‑lived resources (processes, browsers, connections). Calls after session creation reference that state using a `session_name`/`session_id`. Examples include:
  - Bash session: interactive shell process bound to a session.
  - Web browser: Playwright browser/context and page per session.
  - MCP server: spawned stdio server process, tracked by numeric `session_id`.

## Behavioral Differences (at a glance)

- Session scope
  - Stateless: no session is created or referenced; every call stands alone.
  - Stateful: explicit session lifecycle (create → use → optional restart/terminate); each call includes the session identifier.

- State location
  - Stateless: any “state” is external (filesystem, stdout/stderr). No retained in‑memory state between calls.
  - Stateful: in‑memory objects and/or long‑lived processes/resources held per session.

- Isolation
  - Stateless: no built‑in per‑subtask isolation beyond parameter validation and filesystem boundaries.
  - Stateful: per‑session isolation (separate processes/contexts), typically managed by a session controller.

- Failure/recovery
  - Stateless: retry is usually safe when operations are idempotent; recovery is re‑invocation with corrected inputs.
  - Stateful: recovery may require restarting the session or tearing down/re‑creating long‑lived resources.

## When to Choose Which

- Choose stateless when operations are discrete, idempotent, and can be expressed entirely via parameters (e.g., read/modify one file, parse, format, compute).
- Choose stateful when the tool needs continuity across steps (terminal, browser navigation, protocol handshakes, streaming sessions) or benefits from amortizing setup costs (browser/context, subprocess startup).

---

## Design Practices — Common to All Tools

- API contracts
  - Define a stable JSON‑RPC surface; validate inputs with Pydantic models.
  - Reject unknown fields (`model_config = {"extra": "forbid"}`) to catch typos early.
- Errors
  - Raise `ToolException` for user‑correctable issues; let the RPC layer map unexpected exceptions to structured errors.
  - Write messages that guide remediation (which field, allowed range, next action).
- Output shape
  - Return typed models/aliases; keep fields consistent across verbs (e.g., `error`, `info`, `result`).
  - Truncate or page large payloads; include minimal, useful context (e.g., snippets with line numbers).
- Timeouts & budgets
  - Bound every operation; no indefinite waits. Use backoff/retries only for idempotent calls and transient failures.
- Security
  - Enforce least privilege (path allowlists/absolute paths, deny hidden/system paths unless explicit); sanitize any subprocess args; never echo secrets.
- Observability
  - Emit minimal, structured logs with start/end/duration and truncated outputs; avoid logging full content.
- Testing
  - Cover happy paths, validation errors, and failure modes; keep tests deterministic and offline; add large‑output truncation tests.

## Design Practices — Stateless Tools

- Self‑contained inputs
  - Require all needed context via parameters; don’t rely on prior calls.
- Idempotency & safety
  - Prefer idempotent operations. If side effects exist (e.g., writing files), provide a dry‑run or echo‑diff mode where feasible.
- Parameter modeling
  - For multiple verbs, use a discriminated union (single RPC method with `command: Literal[...]`) to keep the surface small and coherent.
- Deterministic output
  - Normalize line endings, expand tabs where readability matters, sort listings consistently, and apply predictable truncation.
- Concurrency
  - Avoid global mutable caches. If cross‑call artifacts are needed (e.g., temp history), ensure concurrency safety (atomic writes/locks) and bound size/TTL.

## Design Practices — Stateful Tools

- Session lifecycle
  - Provide `new_session` to create sessions; require `session_name`/`session_id` on all verbs; offer `restart` and `terminate/kill`. Consider `list_sessions` for administration.
- Isolation
  - Use a session controller to store/lookup sessions; ensure no cross‑session leakage (env, FS, network). Use per‑session temp dirs when possible.
- Resource management
  - Encapsulate long‑lived resources (processes, browser contexts, sockets) behind a session class; implement graceful shutdown and forced kill; cap concurrent sessions; add idle eviction (TTL).
- Concurrency & ordering
  - Protect session maps during creation/teardown; serialize or safely parallelize per‑session actions as appropriate.
- Resilience/health
  - Provide health checks/pings; auto‑recover where safe (e.g., restart crashed process). Surface explicit “session lost” errors otherwise.
- Backpressure & timeouts
  - Bound wait strategies (e.g., interactive shells: “wait for output” vs “idle timeout”); document behavior and defaults.
- Security
  - Prevent privilege escalation across sessions; sanitize subprocess inputs; lock down network access to permitted endpoints only; redact sensitive values in logs.
- Observability
  - Tag logs/metrics with session id; record lifecycle events (created, restarted, terminated), durations, failure reasons; sample large outputs.

---

## Documentation Practices — Stateless Tools

- Overview
  - Purpose, side effects, inputs/outputs, and non‑goals.
- API
  - One RPC entry with `command` variants; include parameter tables (types, defaults, constraints) and result schema; show 1–2 minimal examples per command.
- Validation rules
  - Path rules (absolute/relative, hidden/system handling), size limits, truncation policy, accepted encodings.
- Error semantics
  - Map common conditions to `ToolException` messages and show sample error payloads.
- Security notes
  - Filesystem/network boundaries, redaction behavior, and denied operations.
- Limits
  - Max payload sizes, timeouts, performance characteristics.

## Documentation Practices — Stateful Tools

- Model & lifecycle
  - Diagram and text describing create → use → restart/terminate; enumerate resources held and their limits.
- Session contract
  - How `session_name`/`session_id` are formed, expiry/TTL rules, isolation guarantees, and recovery from “lost session”.
- API
  - Lifecycle endpoints and verbs; required session identifier; parameter tables and result schemas; ordering/causality expectations when relevant.
- Time & limits
  - Idle timeout behavior, max `wait_for_output`, max sessions, memory/CPU caps, eviction policy.
- Error semantics
  - Exhaustive list of lifecycle/verb errors (unknown session, terminated process, timeouts, backpressure) with examples and remediation advice.
- Security & operations
  - Access boundaries and sandboxing; operational playbook for cleanup/recovery and diagnostics.
- Examples
  - End‑to‑end flows (create → multiple commands → restart/terminate), including a fault injection example.

---

## Implementation Templates (sketches)

Stateless (one RPC; multiple commands via discriminated union):

```python
# tool_types.py
from typing import Annotated, Literal
from pydantic import BaseModel, Discriminator, RootModel

class BaseParams(BaseModel):
    # define explicit, self-contained inputs
    ...

class DoThingParams(BaseParams):
    command: Literal["do_thing"] = "do_thing"
    arg: str

class OtherThingParams(BaseParams):
    command: Literal["other_thing"] = "other_thing"
    n: int = 1

class MyToolParams(RootModel):
    root: Annotated[DoThingParams | OtherThingParams, Discriminator("command")]
```

```python
# json_rpc_methods.py
from ..._util.json_rpc_helpers import validated_json_rpc_method
from .tool_types import MyToolParams, DoThingParams, OtherThingParams

@validated_json_rpc_method(MyToolParams)
async def my_tool(params: MyToolParams) -> str:
    match params.root:
        case DoThingParams(arg=arg):
            return await do_thing(arg)
        case OtherThingParams(n=n):
            return await other_thing(n)
```

Stateful (session lifecycle + verbs):

```python
# controller.py
from ..._util.session_controller import SessionController

class Controller(SessionController[Session]):
    async def new_session(self) -> str:
        return await self.create_new_session("MySession", Session.create)

    async def do(self, session_name: str, arg: str) -> Result:
        return await self.session_for_name(session_name).do(arg)
```

```python
# json_rpc_methods.py
@validated_json_rpc_method(NoParams)
async def my_new_session(_: NoParams) -> NewSessionResult:
    return NewSessionResult(session_name=await controller.new_session())

@validated_json_rpc_method(DoParams)
async def my_do(params: DoParams) -> Result:
    return await controller.do(params.session_name, params.arg)
```

---

## Checklist Summary

- Stateless
  - Self‑contained inputs; idempotent where possible; deterministic outputs; safe concurrency; discriminated union API; clear validation and truncation; comprehensive docs for commands, limits, and errors.
- Stateful
  - Full session lifecycle; per‑session isolation; robust resource management, timeouts and backpressure; session‑tagged observability; security hardening; docs covering lifecycle, limits, and operational playbooks.

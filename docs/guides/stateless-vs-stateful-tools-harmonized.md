# Stateless vs Stateful Tools — Harmonized (Inspect AI + Tool Support)

This canonical guide consolidates and supersedes the perspectives in:
- Stateless vs Stateful Tools (Inspect Tool Support)
- What is the difference between stateless and stateful tools?

It preserves Inspect AI examples (e.g., `store_as()`, `web_surfer()`, `react()` MCP handling) while adopting the structured API/session templates, JSON‑RPC + Pydantic modeling, and checklists from Inspect Tool Support.

## Audience & Scope
- For contributors implementing tools used by Inspect AI agents and via the Tool Support JSON‑RPC layer.
- Focus: precise definitions, session contracts, design/documentation practices, and ready‑to‑use templates.

## Canonical Definitions

- Stateless tool: Does not retain in‑memory/process state between calls. Each invocation is self‑contained; all needed context arrives via parameters. Any persistence (e.g., writing files) occurs via external side effects, not via an in‑memory session.

- Stateful tool: Maintains per‑session state in memory or through long‑lived resources (processes, browsers, connections). Calls after session creation reference that state with a `session_name`/`session_id`.

## Examples

- Stateless
  - In‑process text editor verbs: `view`, `create`, `str_replace`, `insert`, `undo_edit` (operate from parameters + filesystem; no session id).
  - One‑shot compute tools: `python()` or `bash()` when executed as isolated, fresh processes with no retained env/WD/history.

- Stateful
  - `bash_session()`: interactive shell process with retained prompt/WD/env.
  - `web_browser()`: Playwright browser/context and page retained across navigations.
  - MCP server sessions: spawned stdio servers tracked by `session_id`.

## Behavioral Differences (At a Glance)

- Session scope
  - Stateless: no session lifecycle; each call stands alone.
  - Stateful: explicit lifecycle (create → use → restart/terminate); every verb references the session id/name.

- State location
  - Stateless: external only (filesystem, stdout/stderr); no retained in‑memory state between calls.
  - Stateful: in‑memory objects and/or long‑lived resources per session.

- Isolation
  - Stateless: parameter validation + FS boundaries only.
  - Stateful: per‑session isolation (separate processes/contexts) via a session controller.

- Failure/recovery
  - Stateless: safe to retry when idempotent; recovery = re‑invoke with corrected inputs.
  - Stateful: may need session restart/teardown and re‑creation.

## When to Choose Which
- Prefer stateless for discrete, idempotent operations expressible entirely via parameters (read/modify a file, parse, format, compute).
- Choose stateful when continuity across steps is needed (terminal use, browser navigation, protocol handshakes, streaming) or to amortize setup costs (browser/context, subprocess startup).

## Inspect AI Integration Patterns

- `store_as()` for state persistence: Use to retain stateful context across invocations (e.g., `web_surfer()` storing message history) and pass an `instance` to isolate per‑instance state.
- MCP connections: Stateful servers require persistence; the `react()` agent manages these via `mcp_connection()` so sessions remain valid across tool calls.

## API & Session Contracts (JSON‑RPC + Pydantic)

Common guidance
- Define a stable JSON‑RPC surface; validate inputs with Pydantic models.
- Reject unknown fields: `model_config = {"extra": "forbid"}` to catch typos early.
- Raise `ToolException` for user‑correctable issues; allow unexpected exceptions to map to structured RPC errors.
- Return typed models/aliases; keep field names consistent (e.g., `error`, `info`, `result`).

### Stateless Template (single RPC; discriminated union)

```python
# tool_types.py
from typing import Annotated, Literal
from pydantic import BaseModel, Discriminator, RootModel

class BaseParams(BaseModel):
    ...  # explicit, self-contained inputs

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

Stateless operational notes
- Self‑contained inputs; do not rely on call ordering.
- Prefer idempotent operations; provide dry‑run/echo‑diff where feasible for side effects.
- Deterministic outputs: normalize line endings, predictable truncation, sorted listings.
- Concurrency: avoid global mutable caches; ensure any cross‑call artifacts are safe (atomic writes/locks) and bounded (size/TTL).

### Stateful Template (session lifecycle + verbs)

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

Stateful operational notes
- Session lifecycle: `new_session` → verbs (`do`, etc.) → `restart`/`terminate`; consider `list_sessions`.
- Isolation: store/lookup sessions via controller; no cross‑session leakage (env/FS/network). Prefer per‑session temp dirs.
- Resource management: encapsulate long‑lived resources; graceful shutdown and forced kill; cap concurrent sessions; idle eviction (TTL).
- Concurrency & ordering: protect session maps; serialize or safely parallelize per‑session actions.
- Resilience/health: health checks/pings; auto‑recover where safe; explicit “session lost” errors otherwise.
- Backpressure & timeouts: bound wait strategies; document defaults.
- Security: sanitize subprocess inputs; least privilege; redact sensitive values.
- Observability: tag logs/metrics with session id; record lifecycle events and durations.

## Concurrency & Parallelism Defaults
- Stateless tools: parallel‑friendly by default (no retained state). If global side effects exist, document constraints.
- Stateful tools: often `parallel=False` per session to avoid state races; if parallelizing, define ordering/locking semantics.

## Documentation Practices

- Stateless docs
  - Overview: purpose, side effects, inputs/outputs, non‑goals.
  - API: single RPC with `command` variants; parameter tables and result schema; 1–2 minimal examples per command.
  - Validation: path rules, size limits, truncation policy, encodings.
  - Errors: `ToolException` mapping and sample payloads.
  - Security: FS/network boundaries; redaction behavior; denied ops.
  - Limits: payload sizes, timeouts, performance characteristics.

- Stateful docs
  - Model & lifecycle: create → use → restart/terminate; enumerate resources and limits.
  - Session contract: id formation, expiry/TTL, isolation guarantees, recovery from lost sessions.
  - API: lifecycle endpoints and verbs; ordering/causality expectations.
  - Time & limits: idle timeout, max `wait_for_output`, max sessions, eviction policy.
  - Errors: lifecycle/verb errors (unknown session, terminated process, timeouts, backpressure) with remediation.
  - Security & ops: sandboxing boundaries; cleanup/recovery and diagnostics playbook.
  - Examples: end‑to‑end flow including a fault injection scenario.

## Inspect AI Notes (Practical)
- Use `store_as()` to persist state and an `instance` key to isolate concurrent stateful tool instances.
- For MCP servers, prefer agent strategies (e.g., `react()` with `mcp_connection()`) that keep connections alive across calls.

## Checklist Summary

- Stateless
  - Self‑contained inputs; idempotent where possible; deterministic outputs; safe concurrency; discriminated‑union API; clear validation/truncation; comprehensive docs for commands, limits, and errors.

- Stateful
  - Full session lifecycle; per‑session isolation; robust resource management, timeouts and backpressure; session‑tagged observability; security hardening; docs covering lifecycle, limits, and operational playbooks.

## Related Docs
- Original perspectives retained for context:
  - [Stateless vs Stateful Tools (Inspect Tool Support)](./archive/stateless-vs-stateful-tools.md)
  - [What is the difference between stateless and stateful tools?](./archive/stateless-vs-stateful-tools-1.md)

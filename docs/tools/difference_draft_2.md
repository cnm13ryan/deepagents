
**1) Assumptions**

* You want one **unified, drop‑in markdown document** that compares how four frameworks define and use *tools*: **Inspect‑AI**, **LangChain/LangGraph**, **OpenAI Agents (Python SDK)**, and **Google ADK**.
* Scope is **semantics and practical use** of “tools” (definition, typing/binding, execution venue, built‑ins, safety, context/state, long‑running semantics, interop, observability, fit).
* Source material = your uploaded draft; this is a **synthesis/normalization** across those notes.&#x20;

---

**2) Plan (+ single tool)**

* **Tool:** none (local synthesis/refactor; no web browsing needed).
* **Approach:** (a) normalize terminology, (b) produce one side‑by‑side table, (c) add minimal “hello tool” examples, (d) capture gotchas & selection heuristics, (e) include acceptance checks.

---

## 3) Step—Execution (artifact)

# Tools Across Agent Frameworks — A Unified Comparison

*What each framework means by a “tool,” how you declare/bind it, where it runs, and what that implies for shipping and safety. Based on your draft comparison.*&#x20;

---

## 1) Big picture in one glance

| Axis                              | **Inspect‑AI**                                                                                                   | **LangChain / LangGraph**                                                                                    | **OpenAI Agents (Python SDK)**                                                                                                                | **Google ADK (Agent Dev Kit)**                                                                                                                                  |
| --------------------------------- | ---------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Center of gravity**             | **Evaluations** & controlled agent runs; tools expand abilities during a measured run.                           | **Applications/graphs**; tools are building blocks in chains/graphs.                                         | **Runtime agent apps**; tools are hosted capabilities or your functions.                                                                      | **Runtime agent apps**; tools with rich per‑tool context & long‑running support.                                                                                |
| **What is a “tool”?**             | Typed Python callable registered via `inspect_ai.tool`; model can call it during eval.                           | Schema’d callable (e.g., `@tool`/`StructuredTool`); used via `.bind_tools`; executed in graphs (`ToolNode`). | Three kinds: **Hosted tools** (e.g., WebSearch, FileSearch, Computer, Code Interpreter), **Function tools** (your Python), **Agent‑as‑tool**. | **FunctionTool**, **LongRunningFunctionTool**, **Agent‑as‑Tool**; schema from signature/docstring.                                                              |
| **How tools are advertised**      | Provided to solver/agent (e.g., `use_tools([...])`) inside an eval task/loop.                                    | `llm.bind_tools([...])` exposes tools; graph decides when/how to execute.                                    | Attach tools to an `Agent`; agent loop invokes as model requests.                                                                             | Register tools on an agent; ADK derives schema and routes calls.                                                                                                |
| **Execution venue & isolation**   | Inline or **sandboxed** (Docker/VM) with time/resource limits; per‑sample isolation.                             | No built‑in sandbox; you provide isolation if needed.                                                        | **Hosted tools** run on OpenAI infra; function tools run in your process (plus a local shell option).                                         | Runs in your runtime; strong **ToolContext** primitives; separate GKE code executor option.                                                                     |
| **Human‑in‑loop / approval**      | **First‑class approval policies** (human/automatic) per tool/action.                                             | Possible via patterns/how‑tos; not enforced by core.                                                         | Guardrails & tracing; human steps are orchestration‑level patterns.                                                                           | Built‑in flow controls in ToolContext (e.g., escalate/transfer/skip).                                                                                           |
| **Built‑ins / standard tools**    | “Batteries included”: web search, browser, bash/python, stateful shells, desktop “computer”, text editor, think. | Large ecosystem via integrations; community‑driven catalog.                                                  | **Hosted**: WebSearch, FileSearch (vector store), Computer, CodeInterpreter, Hosted MCP, ImageGen, LocalShell; can mix.                       | **Built‑ins**: Google Search, Code Execution, GKE executor, Vertex AI Search, BigQuery. **Constraint**: one built‑in per root agent; not allowed in sub‑agents. |
| **Context/state passed to tools** | Eval transcript & scoring context; artifacts/logging integrated.                                                 | Up to you (Runnables + your state); LangSmith for tracing.                                                   | Session & run context optional; you wire app state/services.                                                                                  | **ToolContext** with namespaced session state, **artifacts**, **memory**, **auth hooks**, flow controls.                                                        |
| **Long‑running semantics**        | Eval‑loop controls; timeouts/limits; focus on reproducibility.                                                   | Handle long tasks in your graph/services.                                                                    | Long runs handled at workflow/runtime level; tools stream events.                                                                             | **First‑class** `LongRunningFunctionTool` (pause/resume with intermediate updates).                                                                             |
| **Interop (MCP/OpenAPI/agents)**  | **MCP** native; can import many tools; **Agent Bridge** runs 3rd‑party agents under Inspect.                     | Wrap anything as a tool; MCP not a core primitive.                                                           | **Hosted MCP** tool; can nest **agents‑as‑tools**.                                                                                            | **OpenAPIToolset** → many REST tools from a spec; **MCPToolset**; agents‑as‑tools.                                                                              |
| **Observability**                 | Rich **eval logs/transcripts**, VS Code viewer.                                                                  | **LangSmith** tracing optional; eval separate.                                                               | Built‑in tracing/stream events; integrations with external observability.                                                                     | Traces + per‑tool context surfaces; durable artifacts/memory.                                                                                                   |
| **Security posture**              | Emphasis on **sandboxing** & approval for risky tools.                                                           | BYO isolation & policy.                                                                                      | Hosted tools isolated on provider; function tools = your responsibility.                                                                      | App‑level isolation; ToolContext‑level auth & controls.                                                                                                         |
| **Typical fit**                   | Red‑team/eval harnesses; measured agent tasks.                                                                   | Production graphs/agents with broad integrations.                                                            | Production agents with mix‑and‑match hosted + function tools.                                                                                 | Production agents needing rich **tool context**, **OpenAPI ingestion**, or **durable** long‑running tools.                                                      |

> This table condenses the positions and constraints surfaced in your draft, including ADK’s built‑in composition limit and Inspect’s sandbox/approval guarantees.&#x20;

---

## 2) Minimal “hello tool” in each

> These snippets show each framework’s definition shape and return semantics.&#x20;

**Inspect‑AI**

```python
from inspect_ai.tool import tool

@tool
def add():
    async def execute(x: int, y: int):
        """Add two numbers."""
        return x + y
    return execute
```

**LangChain / LangGraph**

```python
from langchain_core.tools import tool

@tool
def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b

llm_with_tools = llm.bind_tools([multiply])  # model decides when to call
```

**OpenAI Agents (Python SDK)**

```python
from agents import Agent, function_tool

@function_tool
def add(a: int, b: int) -> str:
    """Add two integers."""
    return str(a + b)

agent = Agent(name="assistant", tools=[add])
```

**Google ADK**

```python
from adk import ToolContext  # illustrative import

def add(a: int, b: int, tool_context: ToolContext) -> dict:
    """Add two integers."""
    return {"sum": a + b}  # ADK prefers dict-shaped outputs
```

---

## 3) Design implications & selection heuristics

* **Need measured, reproducible tool use with containment?** Use **Inspect‑AI** (sandbox + approval + logs).&#x20;
* **Want to orchestrate graphs of tools with broad integrations?** Use **LangChain/LangGraph**; add your own isolation where needed.&#x20;
* **Prefer turnkey hosted capabilities you can mix (search + file + computer)?** Use **OpenAI Agents**; keep function tools for portability.&#x20;
* **Need per‑tool state/artifacts/auth, OpenAPI→tools, and built‑in long‑running semantics?** **Google ADK** fits—mind its **built‑in tool composition limits**.&#x20;

---

## 4) Gotchas & edge cases

* **ADK built‑ins:** per root agent **only one built‑in** and **none in sub‑agents**; compose via multiple agents + agent‑as‑tool.&#x20;
* **OpenAI function tools:** custom handlers often **return strings**; standardize adapters if your app wants structured outputs.&#x20;
* **LangChain safety:** no default sandbox—wrap risky tools behind service boundaries or containers.&#x20;
* **Inspect scope:** built for **eval harnesses**; don’t mistake logs/approval as a full production runtime.&#x20;

---

## 5) Glossary (aligned terms)

* **Tool:** named, schema’d callable the model may invoke with structured args; framework validates, executes, and returns result.
* **Binding / Advertising:** mechanism to expose tools to the model (e.g., `bind_tools`, `use_tools`).
* **Sandbox (Inspect):** containerized execution with CPU/mem/net limits, per‑sample isolation.
* **Hosted tool (OpenAI):** provider‑run capability attached to an agent (e.g., web search, computer).
* **ToolContext (ADK):** per‑tool state/artifacts/memory/auth + flow controls used inside the call.&#x20;

---

## 6) Acceptance checks

* A **single table** compares all four frameworks across **purpose, definition, binding, execution/isolation, oversight, built‑ins, state/context, long‑running, interop, observability, security, fit**.
* **Hello‑tool** examples included for all four.
* **Constraints** (e.g., ADK built‑ins; Inspect sandbox/approval guarantees) are explicitly captured.
* In‑line **citation to the provided draft** appears where claims are made.&#x20;

---

**End of artifact.**

---

**4) Progress**

* Normalized and consolidated overlapping comparisons into one consistent markdown doc with a single table + examples.
* Preserved sharp constraints (ADK built‑ins, Inspect sandbox/approval) and patterns (LangGraph `ToolNode`, Agents hosted tools).&#x20;

**5) Next steps (pick one)**

* If helpful, I can **add a “feature‑matrix” CSV** (yes/no/notes) for quick procurement/legal review.
* Or draft **one equivalence demo** (same task implemented in all four) to compare traces, latency, and safety envelope.

**6) Open Qs**

* Do you want **cost/latency** columns added (by scenario), or keep this framework‑semantic only?
* Should we add **interop recipes** (e.g., “ADK OpenAPI → Agents MCP → LangChain wrapper”)?

**7) Risks & Mitigations**

* **Version drift** across fast‑moving docs → pin versions and re‑verify before committing architecture.
* **Security gaps** if risky tools run unsandboxed → isolate in services/containers and add approval where available.

**Confidence:** High on synthesis fidelity relative to your draft; medium on vendor specifics as they evolve (suitable for architecture notes, re‑verify before implementation).&#x20;

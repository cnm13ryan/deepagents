What is the difference between Inspect-AI tools and LangChain tools?


**1) Clarify**
**Goal.** Contrast “Inspect‑AI tools” with “LangChain tools,” focusing on what they are, where they fit, and practical implications.
**Inputs.** Your question only.
**Assumptions (confident).** “Inspect‑AI” refers to the UK AI Safety Institute’s *Inspect* eval framework (`inspect_ai`) and its tool system, not OpenAI’s legacy “Evals.” ([Inspect][1])
**Success.** You get a crisp mental model + a side‑by‑side you can drop into a design doc, with primary docs cited.

---

**2) Decompose**

* What problem each framework is pointed at.
* What a “tool” means in each.
* How tools are declared, bound to models, executed, secured, and audited.
* Interop and when you’d pick one vs the other.

---

**3) Evidence (primary docs)**
I rely on the official Inspect docs for tool basics, standard tools, MCP, sandboxing, and approval; and on LangChain/LangGraph docs for tool concepts, `@tool`/`StructuredTool`, `.bind_tools`, execution via `ToolNode`, and human‑in‑the‑loop patterns. Citations are in‑line below.

---

**4) Plan → Step → Progress**
**Plan.** Build a one‑page comparison table, then give short examples and selection guidance. Tooling: web search only (recency + niche).
**Step (artifact).** The table below.
**Progress.** Table + examples delivered; sources linked.

---

### Inspect‑AI tools vs LangChain tools (at a glance)

| Axis                             | Inspect‑AI tools                                                                                                                                                                                                                     | LangChain tools                                                                                                                                                                                                                             |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Primary purpose**              | Purpose‑built for *evaluations* and controlled agent runs. Tools expand model abilities during a test run and are tightly integrated with Inspect’s transcripts, scoring, and limits. ([Inspect][1])                                 | General framework for building *applications* and agents. Tools are building blocks an agent can call during reasoning/graphs. ([LangChain][2])                                                                                             |
| **What is a “tool”?**            | A typed Python function registered via `@tool` (`inspect_ai.tool`) that the model can call; Inspect ships many built‑ins (bash, python, web\_search, web\_browser, computer, text\_editor, think). ([Inspect][3])                    | A callable with schema (often via `@tool` or `StructuredTool`) that implements the Runnable interface; used with models via `.bind_tools()` and executed by chains/graphs (e.g., LangGraph `ToolNode`). ([LangChain][2], [LangChain AI][4]) |
| **Binding to models**            | Passed to Inspect solvers/agents (e.g., `use_tools([...]); react(...)`). Inspect handles tool metadata, choice, and transcripts. ([Inspect][1])                                                                                      | Tools are *bound* to a model (`llm.bind_tools(tools)`) so the model can decide when to call them. Graph execution commonly uses `ToolNode`. ([LangChain][2], [LangChain AI][5])                                                             |
| **Execution & safety**           | First‑class sandboxing (Docker/K8s/VM) for untrusted code, with timeouts, resource limits, and per‑sample isolation. ([Inspect][6])                                                                                                  | No built‑in sandbox; you provide your own execution/isolation if tools run risky code. (Patterns exist, but up to you.) ([LangChain][2])                                                                                                    |
| **Human approval**               | Built‑in approval policies (human and/or automatic), per‑tool or per‑action; can escalate and annotate calls with “views.” ([Inspect][7])                                                                                            | Possible via custom flows; there’s a how‑to for adding a human‑in‑the‑loop, but it’s not enforced by default. ([LangChain][8])                                                                                                              |
| **Standard library / built‑ins** | Batteries included: web search (internal providers like OpenAI/Anthropic/Gemini/Grok/Perplexity or external Tavily/Exa/Google), browser, bash/python, stateful bash sessions, desktop “computer,” text editor, think. ([Inspect][9]) | Large ecosystem via integrations & toolkits; you assemble components (search, retrievers, APIs). Core “tool” is a schema + executor; catalog is community‑driven. ([LangChain][2])                                                          |
| **MCP (Model Context Protocol)** | Native: can expose *hundreds* of tools from MCP servers (local, HTTP, sandbox; even “remote MCP” executed by model providers). ([Inspect][10])                                                                                       | Not a core primitive; you can integrate external services as tools, but MCP isn’t a first‑class, documented pathway in LangChain core. ([LangChain][2])                                                                                     |
| **Tracing & eval logs**          | Rich eval logs/transcripts with tool events; VS Code viewer provided. ([Inspect][11])                                                                                                                                                | Tracing via LangSmith if opted‑in; tools are Runnables so they trace, but eval‑grade scoring is separate from core tools. ([LangChain][2])                                                                                                  |
| **Typical fit**                  | Red‑team/eval harnesses, capability/agentic benchmarks, research agents where *reproducibility, guardrails, and tool approval* matter. ([Inspect][6])                                                                                | Production agents & apps, graph‑based workflows (LangGraph), broad integrations; you add guardrails as needed. ([LangChain AI][5], [LangChain][12])                                                                                         |

---

### Minimal “hello tool” in each

**Inspect‑AI** (typed tool with metadata; great for evals & sandboxed calls)

```python
from inspect_ai.tool import tool

@tool
def add():
    async def execute(x: int, y: int):
        """Add two numbers.
        Args:
            x: First addend.
            y: Second addend.
        """
        return x + y
    return execute
```

Registered tools are given to a solver/agent (e.g., `use_tools([add()]); generate()`), with optional sandbox/approval. ([Inspect][1])

**LangChain** (function → tool; bound to a model; executed via graph)

```python
from langchain_core.tools import tool

@tool
def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b

llm_with_tools = llm.bind_tools([multiply])  # model chooses when to call
```

Execution often happens inside a LangGraph with `ToolNode`, which runs tool calls in parallel as needed. ([LangChain][2], [LangChain AI][4])

---

### When to use which (pragmatic)

* **Choose Inspect tools** when you need *controlled, reproducible* tool use with **built‑in sandboxing and human approval** (e.g., code‑exec/browser agents under test, CTF‑style evals, risk‑managed red‑teaming). ([Inspect][6])
* **Choose LangChain tools** when shipping *applications/agents* where you want broad **provider integrations**, graph orchestration (LangGraph), and you’ll architect your own safety envelope. ([LangChain][2], [LangChain AI][5])
* **Interop.** If you already have LangChain agents but want Inspect’s eval/logs/approval, Inspect’s *Agent Bridge* shows how to run third‑party agents (including LangChain) under Inspect’s model/router so you can evaluate them with Inspect’s plumbing. ([Inspect][13])

---

### Definitions (to align terms)

* **Tool (both)**: a named, schema’d callable the model can request with structured args; the framework validates/executes it, returns a result, and records the event. ([LangChain][2], [Inspect][1])
* **Binding (LangChain)**: `llm.bind_tools([...])` advertises tools to the model; execution typically via graph nodes like `ToolNode`. ([LangChain][2], [LangChain AI][4])
* **Sandbox (Inspect)**: containerized environment for tool code with CPU/mem/net limits, per‑sample isolation, and exec/file APIs. ([Inspect][6])
* **Approval (Inspect)**: policy that intercepts tool calls, enabling human/auto decisions per tool/action; can modify/deny/escalate. ([Inspect][7])
* **MCP (Inspect)**: standard protocol to import/export tool catalogs; Inspect can connect to stdio/HTTP/sandbox MCP servers and even delegate remote execution via provider. ([Inspect][10])

---

### Pitfalls & trade‑offs

* **Security model.** LangChain won’t isolate risky tools for you; plan your own sandbox or service boundary. Inspect bakes this in. ([Inspect][6], [LangChain][2])
* **Tool sprawl.** Too many tools harms tool‑selection; both docs recommend small, well‑named, narrowly‑scoped tools. ([LangChain][2])
* **MCP nuance.** Inspect’s MCP is turnkey; in LangChain you’d wrap MCP servers yourself as tools—more flexibility, more glue. ([Inspect][10], [LangChain][2])
* **Human‑in‑loop.** Inspect’s approval is first‑class. In LangChain you’ll implement a pattern (there’s a how‑to), which is extra engineering but more customizable. ([Inspect][7], [LangChain][8])

---

### Acceptance check (quick)

* You can articulate: “Inspect tools are eval‑oriented with sandbox + approval; LangChain tools are app‑oriented with broad integrations and graph execution.”
* You can pick a framework per project risk profile and environment.

---

**5) Next steps (options)**

* If you want, I can **map a specific tool** (e.g., a web‑search or code‑exec tool) into both frameworks and show the minimal secure deployment surface (sandbox/docker vs app microservice).
* Or we can **bridge a LangChain agent into Inspect** to evaluate it with approval + logs.

**6) Open Qs**

* Are you optimizing for *eval safety & reproducibility* or *app shipping speed*?
* Do you already rely on MCP servers you want to reuse?

**7) Risks & mitigations**

* **Risk:** Over‑trusting model‑driven code exec. **Mitigate:** Use Inspect sandbox & approvals or isolate in a separate service. ([Inspect][6])
* **Risk:** Tool selection fails with long menus. **Mitigate:** Curate few, descriptive tools; enforce tool choice sparingly. ([LangChain][2])

**Confidence:** High on concepts and differences (drawn from current docs). Medium on your specific constraints until you share them.

[1]: https://inspect.aisi.org.uk/tools.html "Tool Basics – Inspect"
[2]: https://python.langchain.com/docs/concepts/tool_calling/ "Tool calling | ️ LangChain"
[3]: https://inspect.aisi.org.uk/reference/inspect_ai.tool.html "inspect_ai.tool – Inspect"
[4]: https://langchain-ai.github.io/langgraphjs/reference/classes/langgraph_prebuilt.ToolNode.html?utm_source=chatgpt.com "ToolNode | API Reference - GitHub Pages"
[5]: https://langchain-ai.github.io/langgraphjs/how-tos/tool-calling/?utm_source=chatgpt.com "How to call tools using ToolNode"
[6]: https://inspect.aisi.org.uk/sandboxing.html "Sandboxing – Inspect"
[7]: https://inspect.aisi.org.uk/approval.html "Tool Approval – Inspect"
[8]: https://python.langchain.com/docs/how_to/tools_human/ "How to add a human-in-the-loop for tools | ️ LangChain"
[9]: https://inspect.aisi.org.uk/tools-standard.html "Standard Tools – Inspect"
[10]: https://inspect.aisi.org.uk/tools-mcp.html "Model Context Protocol – Inspect"
[11]: https://inspect.aisi.org.uk/vscode.html "VS Code Extension – Inspect"
[12]: https://www.langchain.com/langgraph?utm_source=chatgpt.com "LangGraph - LangChain"
[13]: https://inspect.aisi.org.uk/agent-bridge.html "Agent Bridge – Inspect"

---

What is the difference between Inspect-AI tools and OpenAI Agents python sdk tools?


Below is a crisp, one‑pass comparison—framed for build/readiness and citing primary docs.

---

## 1) Clarify

**Goal.** Explain the difference between **Inspect‑AI “tools”** and **OpenAI Agents Python SDK tools**—what they are, where they run, how you define/use them, and when to pick which.

**Inputs.** None provided.

**Assumptions (high confidence).**

* “Inspect‑AI” refers to the UK AI Security Institute’s *Inspect* library (`inspect_ai`) and its “tools” abstraction used during **evaluations**. (AISI/2025) ([Inspect][1])
* “OpenAI Agents Python SDK tools” refers to the `openai‑agents‑python` SDK’s tool system (Hosted tools, Function tools, Agents‑as‑tools) used to build **agentic apps**. (OpenAI/2025) ([OpenAI GitHub][2])

**Constraints / success criteria.**

* Side‑by‑side, implementation‑level accuracy.
* Primary sources only (Inspect docs, OpenAI Agents SDK docs).
* Actionable “when to use which”.

No blocking questions.

---

## 2) Decompose

Answer the sub‑questions:

1. What a “tool” means in each system.
2. Where those tools execute (hosted/local/sandboxed).
3. How you register/define tools.
4. What’s built‑in.
5. State, orchestration, and observability.
6. Typical use cases and pick‑guidance.

---

## 3) Step — Execution (artifact)

### Inspect‑AI tools vs. OpenAI Agents SDK tools

| Dimension                        | **Inspect‑AI tools**                                                                                                                                                                              | **OpenAI Agents Python SDK tools**                                                                                                                                                                                                                            |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Owner / purpose**              | OSS by **UK AI Security Institute**. A framework to **evaluate** LLMs (benchmarks, scorers, logs). Tools are capabilities models can use **during eval runs**. (AISI/2025) ([Inspect][1])         | Open‑source SDK by **OpenAI** for building **agentic applications/workflows**. Tools let agents take actions in production workflows. (OpenAI/2025) ([OpenAI GitHub][3])                                                                                      |
| **What “tool” means**            | A Python function (or built‑in) the model can call while being evaluated; provided to the model via `use_tools(...)`. (AISI/2025) ([Inspect][1])                                                  | Three classes: **Hosted tools** (OpenAI‑hosted capabilities like Web Search, File Search, Computer, Code Interpreter), **Function tools** (your Python functions with auto schema), and **Agents‑as‑tools** (nest agents). (OpenAI/2025) ([OpenAI GitHub][2]) |
| **How you define custom tools**  | `@tool` decorator returning an async `execute(...)` with typed params + docstrings; Inspect translates model tool‑calls into function invocations during an eval loop. (AISI/2025) ([Inspect][1]) | `@function_tool` (or create `FunctionTool`)—SDK auto‑derives JSON schema from type hints & docstrings; tools can also accept a run context. (OpenAI/2025) ([OpenAI GitHub][2])                                                                                |
| **Built‑in / standard tools**    | Standard set: **web search**, **bash**, **python**, **bash session**, **text editor**, **web browser (headless Chromium)**, **computer (desktop)**, **think**. (AISI/2025) ([Inspect][1])         | Hosted tools (when using OpenAI models): **WebSearchTool**, **FileSearchTool**, **ComputerTool**, **CodeInterpreterTool**, **HostedMCPTool**, **ImageGenerationTool**, **LocalShellTool**. (OpenAI/2025) ([OpenAI GitHub][2])                                 |
| **Where tools run**              | By default inline in the eval process; optionally inside **Docker sandboxes** with a sandbox API for `exec`, file IO, per‑sample files, resource limits. (AISI/2025) ([Inspect][4])               | **Hosted tools** run on OpenAI’s side (e.g., computer‑use, web search, code interpreter). **Function tools** run in your Python process. (OpenAI/2025) ([OpenAI GitHub][2])                                                                                   |
| **MCP (Model Context Protocol)** | Can attach **MCP servers** so models gain access to external tools via the MCP spec. (AISI/2025) ([Inspect][1])                                                                                   | First‑class **MCP** support with helpers for stdio/SSE/streamable servers, plus tool filtering & caching. (OpenAI/2025) ([OpenAI GitHub][5])                                                                                                                  |
| **State & orchestration**        | Tools are used inside **Tasks/Solvers** that drive eval prompts and scoring. Inspect also exposes an “Agents” scaffold for multi‑turn objectives **within evals**. (AISI/2025) ([Inspect][1])     | SDK provides **agent loop**, **handoffs** (delegate between agents), **sessions** (conversation memory), **guardrails**, **tracing**—all aimed at **application runtime**. (OpenAI/2025) ([OpenAI GitHub][3])                                                 |
| **Observability**                | Rich **log viewer**, dataframes, scoring breakdowns, per‑sample transcripts; eval logs viewable in VS Code or browser. (AISI/2025) ([Inspect][6])                                                 | Built‑in **tracing** and visualization for runs; pluggable processors (e.g., Logfire, AgentOps, Braintrust, etc.). (OpenAI/2025) ([GitHub][7])                                                                                                                |
| **Security/isolation knobs**     | **Sandboxing** controls (Docker), per‑sample files, resource caps, explicit error surfaces and retry semantics for non‑idempotent ops. (AISI/2025) ([Inspect][4])                                 | Hosted tools are isolated on OpenAI infra; function tools run in your runtime; guardrails & model‑side structured outputs are available at the SDK level. (OpenAI/2025) ([OpenAI GitHub][3])                                                                  |
| **Primary fit**                  | Building **reproducible evaluations** (benchmarks, agent tasks under measurement) with tool‑use, plus score/compare across runs. (AISI/2025) ([Inspect][1])                                       | Building **production agent flows**—compose tools, multi‑agent handoffs, session memory, hosted capabilities—then ship. (OpenAI/2025) ([OpenAI GitHub][3])                                                                                                    |

**Key take:** both expose “tools” to a model, but **Inspect’s tools exist to measure model behavior** (evaluation harness), while **Agents SDK tools exist to get work done in live agent apps** (orchestrator/runtime).

---

## 4) Progress

* **Fact‑checked** definitions, built‑ins, and execution models directly in primary docs.

  * Inspect: tool basics, standard tools, MCP, sandboxing, logs. (AISI/2025) ([Inspect][1])
  * Agents SDK: tool classes, hosted tools list, function tool schema extraction, agents‑as‑tools, sessions/tracing overview, repo readme. (OpenAI/2025) ([OpenAI GitHub][2], [GitHub][7])
* **Delivered** a side‑by‑side table for quick selection.

Next actionable item (if you want): code stubs showing how to register one equivalent “add” tool in each framework and how each is invoked in a minimal loop—useful for migration/readiness.

---

## 5) Definitions (precise)

* **Inspect tool.** A typed Python callable registered via `@tool` that the model may call during an **eval**; invoked through Inspect’s solver loop (e.g., `use_tools([...]), generate()`). (AISI/2025) ([Inspect][1])
* **Agents SDK tool.** An action callable by an **agent**; either OpenAI‑**hosted** (web search, file search, computer, code interpreter, etc.), a **function tool** (your Python), or an **agent exposed as a tool**. (OpenAI/2025) ([OpenAI GitHub][2])

---

## 6) Logic you can trust

* **Scope difference** drives everything: *evaluation harness* vs *application runtime orchestration*. That’s why Inspect leans into sandboxes/logging/scoring; Agents SDK leans into sessions/handoffs/tracing. The overlap (both can “run tools” or even “agents”) is incidental—their operational center of gravity is different. (Docs corroborate the emphasis in each.) ([Inspect][1], [OpenAI GitHub][3])

---

## 7) Minimal examples (pseudocode)

* **Inspect (eval):**

  ```python
  from inspect_ai.tool import tool
  from inspect_ai import Task, task
  from inspect_ai.solver import use_tools, generate

  @tool
  def add():
      async def execute(x: int, y: int): return x + y
      return execute

  @task
  def t():
      return Task(dataset=[...], solver=[use_tools(add()), generate()])
  ```

  (Pattern per Tool Basics.) ([Inspect][1])

* **Agents SDK (runtime):**

  ```python
  from agents import Agent, Runner, function_tool

  @function_tool
  def add(x: int, y: int) -> int: return x + y

  agent = Agent(name="assistant", tools=[add])
  result = Runner.run_sync(agent, "compute 2+3")
  ```

  (Pattern per SDK tools page.) ([OpenAI GitHub][2])

---

## 8) Tool choice (why these sources)

* Used **Inspect official docs** (AISI) for tool semantics, built‑ins, sandboxing, and logs. ([Inspect][1])
* Used **OpenAI Agents SDK docs + repo** for tool classes, hosted tools, sessions/loop/tracing. ([OpenAI GitHub][2], [GitHub][7])

---

## 9) Selection heuristics (practical)

* **Use Inspect‑AI tools** when your deliverable is an **eval suite** (benchmarks, model‑grading, run‑to‑run comparability, artifacts for analysis). You’ll likely want sandboxing, reproducible logs, and scorers. ([Inspect][1])
* **Use Agents SDK tools** when your deliverable is a **production agent** (multi‑tool tasks, handoffs, web search/computer use, tracing, session memory). Start with hosted tools, add function tools as needed. ([OpenAI GitHub][3])
* **MCP present in both**—choose based on where you need it (under eval vs in app). ([Inspect][1], [OpenAI GitHub][5])

---

## 10) Quality: pitfalls & tests

**Pitfalls**

* Treating Inspect as an app runtime (you’ll end up rebuilding session/serving features it doesn’t aim to provide).
* Assuming Agents SDK hosted tools exist when using a non‑OpenAI model/provider—those hosted tools are tied to OpenAI’s Responses/infra; function tools remain portable. (OpenAI/2025) ([OpenAI GitHub][3])

**Acceptance checks**

* Can you define one “add” tool in each and see it called?
* In Inspect, do you get an eval log with tool‑call traces? (Log Viewer) ([Inspect][6])
* In Agents SDK, do you see a traced run and (optionally) use WebSearchTool/FileSearchTool? ([OpenAI GitHub][2])

---

### TL;DR

* **Inspect tools → eval harness** (measure behavior; sandboxes + logs). (AISI/2025) ([Inspect][1])
* **Agents SDK tools → runtime actions** (ship workflows; hosted tools + function tools + tracing/sessions). (OpenAI/2025) ([OpenAI GitHub][2])

---

**Next steps (if useful):** want code that performs the *same* multi‑turn tool task in both frameworks (e.g., browse→edit file→run code) so you can compare semantics, latency, and logs apples‑to‑apples?

**Open Qs:** none.

**Risks & mitigations:**

* Version drift across docs—pin SDK/library versions in examples; keep an eye on hosted‑tool availability by model/provider. (OpenAI/2025) ([OpenAI GitHub][3])

**Confidence:** High.

[1]: https://inspect.aisi.org.uk/tools.html "Tool Basics – Inspect"
[2]: https://openai.github.io/openai-agents-python/tools/ "Tools - OpenAI Agents SDK"
[3]: https://openai.github.io/openai-agents-python/ "OpenAI Agents SDK"
[4]: https://inspect.aisi.org.uk/sandboxing.html "Sandboxing – Inspect"
[5]: https://openai.github.io/openai-agents-python/mcp/ "Model context protocol (MCP) - OpenAI Agents SDK"
[6]: https://inspect.aisi.org.uk/log-viewer.html "Log Viewer – Inspect"
[7]: https://github.com/openai/openai-agents-python "GitHub - openai/openai-agents-python: A lightweight, powerful framework for multi-agent workflows"

---

What is the difference between google ADK's tools and OpenAI Agent's python SDK tools?

---


Below is a clean, side‑by‑side view of **Google’s Agent Development Kit (ADK) “tools”** versus **OpenAI Agents Python SDK “tools.”** I’m assuming you mean ADK’s Python flavor and OpenAI’s *Agents SDK* (not the older Assistants API). Goal: highlight the model, how you define/host tools, orchestration primitives, and notable constraints—so you can pick the right abstraction for your build.

---

## 1) Clarify

* **Goal:** Compare “tools” between **Google ADK** and **OpenAI Agents (Python SDK)** at the design/usage level.
* **Inputs/constraints:** None provided. I’ll use vendor docs only; call out anything that’s temporally sensitive or has caveats.
* **Success metrics:** A tight diff table + practical takeaways (built‑ins, composition limits, context/state, long‑running support, auth, interop) with citations to official docs.

**Assumptions (high confidence):**

* “Google ADK” = Google’s **Agent Development Kit** (Python) and its tool model. ([Google GitHub][1])
* “OpenAI Agent’s python SDK tools” = OpenAI **Agents SDK (Python)** “tools” (hosted + function tools + agent-as-tool). ([OpenAI GitHub][2])

No questions needed.

---

## 2) Decompose → Sub‑questions answered

### A. What *is* a “tool” in each?

* **ADK:** A modular capability (function/method/another agent) used by an LLM agent. ADK has **Function Tools**, **Long‑Running Function Tools**, and **Agent‑as‑a‑Tool**. ([Google GitHub][3])
* **OpenAI Agents SDK:** Three classes—**Hosted tools** (run alongside the model, e.g., web search, file search, computer use), **Function tools** (any Python function), and **Agents as tools**. ([OpenAI GitHub][2])

### B. How are tools defined and typed?

* **ADK:** Introspects Python signatures and docstrings to build the schema; *recommends/normalizes dict outputs* (non‑dict returns are wrapped). ([Google GitHub][4])
* **OpenAI Agents:** Auto‑generates JSON schema from Python signatures/docstrings via `inspect` + Pydantic; custom `FunctionTool`’s `on_invoke_tool` **must return a string**. ([OpenAI GitHub][2])

### C. Built‑ins (what you get out of the box)?

* **ADK built‑ins:** Google Search grounding (Gemini 2 only), Code Execution, GKE code executor, Vertex AI Search, BigQuery—**but with important composition limits** (see next row). ([Google GitHub][5])
* **OpenAI built‑ins (hosted tools):** WebSearch, FileSearch (OpenAI Vector Stores), ComputerTool (Operator), CodeInterpreter, Hosted MCP, ImageGeneration, plus LocalShell (runs locally). You can define multiple hosted tools on the same agent. ([OpenAI GitHub][2])

### D. Can I mix built‑ins with other tools?

* **ADK:** **Limit today**—per root/single agent, **only one built‑in tool** and **cannot use built‑ins in sub‑agents**; you can combine via multiple agents and agent‑as‑tool instead. ([Google GitHub][5])
* **OpenAI Agents:** Examples show **multiple hosted tools together** (e.g., WebSearch + FileSearch) alongside function tools. ([OpenAI GitHub][2])

### E. “Context” passed into tools (state, artifacts, flow‑control)?

* **ADK ToolContext:** First‑class **session state** with namespaced keys (`app:*`, `user:*`, session, `temp:*`), **artifact** and **memory** services, **auth hooks**, and **post‑tool flow controls** (`skip_summarization`, `transfer_to_agent`, `escalate`). ([Google GitHub][3])
* **OpenAI Agents:** Optional `RunContextWrapper` gives you app‑defined context; **session memory** exists in the SDK (e.g., `SQLiteSession`) but artifact/memory/auth are not baked into a tool context API the way ADK does. ([OpenAI GitHub][2])

### F. Long‑running work & pause/resume

* **ADK:** **LongRunningFunctionTool** is a first‑class tool type—initiate work, send **intermediate updates**, and **pause/resume** the agent run until final result. ([Google GitHub][4])
* **OpenAI Agents:** Tool calls stream events; “long‑running” is handled at the **run/workflow** layer (e.g., Temporal integration, human‑in‑the‑loop patterns), not as a dedicated **long‑running tool type**. ([OpenAI GitHub][6])

### G. Interop with external systems (OpenAPI/MCP/etc.)

* **ADK:** **OpenAPIToolset** auto‑generates `RestApiTool`s from an OpenAPI spec; also has **MCPToolset** to surface MCP servers’ tools as native ADK tools. ([Google GitHub][7])
* **OpenAI Agents:** Built‑in **HostedMCPTool** to expose remote MCP servers; no built‑in OpenAPI‑to‑tool generator (you’d write a function tool or use MCP that wraps your API). ([OpenAI GitHub][2])

### H. Authentication inside tools

* **ADK:** ToolContext supports **auth flows**: `auth_response`, `request_credential(auth_config)`, and docs show how auth ties into `RestApiTool`/OpenAPIToolset & Google APIs. ([Google GitHub][3])
* **OpenAI Agents:** Auth is app‑level—you pass credentials into your function tools or configure hosted tool credentials; no built‑in ToolContext auth flow like ADK’s. (Docs emphasize schema/contexts; auth flow is your code.) ([OpenAI GitHub][2])

### I. “Agents as tools”

* **Both** support turning an agent into a callable **tool** (agent‑as‑tool pattern). ([Google GitHub][4], [OpenAI GitHub][2])

---

## 3) Evidence (inline)

* ADK tools overview & types (Function, Long‑Running, Agent‑as‑Tool). ([Google GitHub][3])
* ADK built‑ins + **composition limits** (one built‑in per agent; not allowed in sub‑agents). ([Google GitHub][5])
* ADK ToolContext: **state**, **artifacts**, **memory**, **flow control**; **auth hooks**. ([Google GitHub][3])
* ADK OpenAPI/MCP toolsets. ([Google GitHub][7])
* OpenAI Agents tools: hosted tools list; function tools auto‑schema; `on_invoke_tool` returns **string**; agents‑as‑tool; conditional enabling. ([OpenAI GitHub][2])
* OpenAI Agents **Memory/Session** concept. ([OpenAI GitHub][8])
* OpenAI Agents long‑running guidance is at run/workflow layer (Temporal/HITL). ([OpenAI GitHub][6])

---

## 4) Plan → Step → Progress

**Plan:**

* Compile a concise diff table across nine dimensions; surface sharp “gotchas”; include doc links.

**Step — Execution (artifact):**

### Quick diff (you can skim)

| Dimension               | Google ADK                                                                                                                                                                                       | OpenAI Agents (Python SDK)                                                                                                                                    |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Tool categories         | Function Tools, **LongRunningFunctionTool**, Agent‑as‑Tool. ([Google GitHub][4])                                                                                                                 | **Hosted tools**, Function tools, Agents as tools. ([OpenAI GitHub][2])                                                                                       |
| Define a tool           | Introspects function signature & docstring; return ideally **dict** (non‑dict is wrapped). ([Google GitHub][4])                                                                                  | Auto‑schema from signature/docstring; custom `FunctionTool.on_invoke_tool` returns **string**. ([OpenAI GitHub][2])                                           |
| Built‑ins               | Google Search, Code Execution, **GKE executor**, Vertex AI Search, **BigQuery**. **Limit: only one built‑in per (root/single) agent; built‑ins not allowed in sub‑agents.** ([Google GitHub][5]) | WebSearch, FileSearch (Vector Stores), ComputerTool, CodeInterpreter, Hosted MCP, ImageGeneration, LocalShell. Can combine in one agent. ([OpenAI GitHub][2]) |
| Composition             | Built‑in(s) constrained; combine via multiple agents + agent‑as‑tool. ([Google GitHub][5])                                                                                                       | Typical to mix **multiple** hosted tools + function tools in one agent. ([OpenAI GitHub][2])                                                                  |
| Context passed to tools | **ToolContext** gives session **state** (with prefixes), **artifacts**, **memory**, **auth**, and **flow control** (`skip_summarization`, `transfer_to_agent`, `escalate`). ([Google GitHub][3]) | Optional `RunContextWrapper` (you define); SDK offers session **memory**, but artifacts/auth/flow‑control are app‑level concerns. ([OpenAI GitHub][8])        |
| Long‑running            | **First‑class**: LongRunningFunctionTool with **intermediate/final updates**; agent runs can pause/resume. ([Google GitHub][4])                                                                  | Handled at **workflow layer** (e.g., Temporal, human‑in‑the‑loop); tool itself is not a special long‑running type. ([OpenAI GitHub][6])                       |
| OpenAPI/MCP             | **OpenAPIToolset** → many `RestApiTool`s from your spec; **MCPToolset** to surface MCP tools natively. ([Google GitHub][7])                                                                      | **HostedMCPTool** (remote MCP servers); no built‑in OpenAPI→tool generator. ([OpenAI GitHub][2])                                                              |
| Authentication          | Built‑in **auth flow hooks** in ToolContext (`request_credential`, etc.); tool docs show config patterns. ([Google GitHub][3])                                                                   | You manage creds in your code or hosted tool setup; no ToolContext auth API. ([OpenAI GitHub][2])                                                             |
| Agents as tools         | Supported (AgentTool). ([Google GitHub][4])                                                                                                                                                      | Supported (`agent.as_tool`). ([OpenAI GitHub][2])                                                                                                             |

**Progress:** Compared the abstractions, constraints, and interop; flagged where each shines, with doc anchors.

---

## 5) Define (formal-ish)

* **ADK Function Tool:** A Python function `f(a: int, b: int, tool_context: ToolContext) -> dict` whose signature/docstring are introspected to a JSON schema the LLM can call. Outputs are dict‑shaped for the agent’s “observation”; the `ToolContext` offers state/artifacts/memory/auth/flow controls. ([Google GitHub][4])
* **ADK LongRunningFunctionTool:** A wrapper around a function that kicks off work and lets the agent **pause**; the client later **continues** the run with intermediate/final results, which the framework packages back to the LLM. ([Google GitHub][4])
* **OpenAI Function Tool:** A Python function—decorated or a `FunctionTool`—with auto‑schema; custom `on_invoke_tool(ctx, args_json)` **returns a string**. Hosted tools run server‑side (except LocalShell which runs locally). ([OpenAI GitHub][2])

---

## 6) Math/Logic

N/A (no arithmetic here).

---

## 7) Algorithms/Code (minimal examples)

* **ADK (Function Tool):** `def add(a: int, b: int, tool_context: ToolContext) -> dict: return {"sum": a+b}` (introspection + dict output). ([Google GitHub][4])
* **OpenAI (Function Tool):** `@function_tool def add(a: int, b: int) -> str: return str(a+b)` or `FunctionTool(on_invoke_tool=...)` (string output from the tool invocation). ([OpenAI GitHub][2])

---

## 8) Tools (meta)

* **One tool used here:** web.run to pull **official** ADK and OpenAI Agents SDK docs; this matters because both stacks are moving targets and the limits (e.g., ADK built‑ins composition) are version‑sensitive. ([Google GitHub][5], [OpenAI GitHub][2])

---

## 9) Practical takeaways

* **Need a built‑in OpenAPI→tool bridge?** ADK’s **OpenAPIToolset** is turnkey; Agents SDK will need your own function tools or an MCP server that wraps your API. ([Google GitHub][7], [OpenAI GitHub][2])
* **Need durable, pause/resume tooling with status updates?** ADK’s **LongRunningFunctionTool** is native. OpenAI leans on **workflow/run orchestration** (e.g., Temporal) rather than a special tool type. ([Google GitHub][4], [OpenAI GitHub][6])
* **Want multiple built‑ins in one agent (search + file search + computer use)?** OpenAI SDK supports that; ADK’s built‑ins are **one per agent** and **not in sub‑agents** right now. Design around it with agent‑as‑tool if you need both. ([OpenAI GitHub][2], [Google GitHub][5])
* **Prefer richer per‑tool context primitives (state/artifacts/memory/auth/flow)?** ADK’s **ToolContext** is opinionated and full‑featured. OpenAI’s `RunContextWrapper` is flexible but you wire most services yourself. ([Google GitHub][3], [OpenAI GitHub][2])

---

## 10) Quality: pitfalls, risks, tests

* **Pitfalls**

  * **ADK built‑in tool limits** surprise teams when they try to mix search + code execution in one agent; split into sub‑agents & compose with agent‑as‑tool. Validate this early. ([Google GitHub][5])
  * **Return‑type mismatches:** ADK expects dict‑like outputs; OpenAI function tools often return strings. Standardize adapters to keep traces/readability clean. ([Google GitHub][3], [OpenAI GitHub][2])
  * **Auth & secrets:** ADK’s ToolContext can request credentials; in OpenAI, handle credentials in your function/hosted tool config. Test secure handling either way. ([Google GitHub][3])

* **Acceptance checks**

  * You can register a function tool in each stack and see the **auto‑generated schema** (types & arg descriptions) in logs/trace. ([Google GitHub][4], [OpenAI GitHub][2])
  * In ADK, call a **LongRunningFunctionTool** and verify intermediate updates and paused run; in OpenAI, verify **streaming events** and (optionally) a Temporal workflow for long tasks. ([Google GitHub][4], [OpenAI GitHub][9])
  * In ADK, try to add two built‑ins to one agent and confirm the documented constraint triggers; in OpenAI, run with WebSearch + FileSearch together. ([Google GitHub][5], [OpenAI GitHub][2])

**Log (decisions):**

* Treated “tools” as first‑class ADK vs Agents SDK concept; privileged official docs; highlighted hard constraints.

---

## Next steps (pick one)

* If you plan to **wrap a REST estate fast**, pilot ADK’s **OpenAPIToolset** on one service and measure tool‑call accuracy and schema coverage. ([Google GitHub][7])
* If you want **one agent with multiple hosted skills** (search + vector + computer use), prototype in OpenAI Agents using **two hosted tools + one function tool** and inspect traces. ([OpenAI GitHub][2])
* If your flows are **approval‑ or SLA‑bound**, run ADK’s **LongRunningFunctionTool** sample and compare with an OpenAI **Temporal** workflow for equivalent latency/observability. ([Google GitHub][4], [OpenAI GitHub][6])

---

## Open questions

* Are you optimizing for **rapid API surface ingestion** (OpenAPI) or **one‑agent multi‑capability** with minimal constraints?
* Do you need **durable long‑running** tasks inside the tool abstraction itself, or is **workflow‑level** durability okay?

---

## Risks & mitigations

* **Docs are moving:** Re‑check ADK built‑in composition limits and tool lists before locking architecture. (Mitigate with a spike and CI checks against templates.) ([Google GitHub][5])
* **Vendor coupling:** ADK’s Google Search & BigQuery tools tie you to Google infra; OpenAI’s hosted tools tie you to OpenAI Vector Stores/Operator. Keep function tools for portability. ([Google GitHub][5], [OpenAI GitHub][2])

---

### Bottom line (one‑liner)

* **ADK** gives you **strong per‑tool context/state/auth and first‑class long‑running tools**, plus an **OpenAPI→tool** bridge—at the cost of **stricter built‑in composition** today. ([Google GitHub][4])
* **OpenAI Agents** gives you **richer hosted tool variety and easy mixing** inside one agent, with clean function‑tool ergonomics—long‑runs handled at the **workflow** level. ([OpenAI GitHub][2])

**Confidence:** High on the broad differences; medium on fast‑changing limits (verify on your specific versions).

[1]: https://google.github.io/adk-docs/ "Agent Development Kit"
[2]: https://openai.github.io/openai-agents-python/tools/ "Tools - OpenAI Agents SDK"
[3]: https://google.github.io/adk-docs/tools/ "Tools - Agent Development Kit"
[4]: https://google.github.io/adk-docs/tools/function-tools/ "Function tools - Agent Development Kit"
[5]: https://google.github.io/adk-docs/tools/built-in-tools/ "Built-in tools - Agent Development Kit"
[6]: https://openai.github.io/openai-agents-python/running_agents/?utm_source=chatgpt.com "Running agents - OpenAI Agents SDK"
[7]: https://google.github.io/adk-docs/tools/openapi-tools/?utm_source=chatgpt.com "OpenAPI tools - Agent Development Kit - Google"
[8]: https://openai.github.io/openai-agents-python/ref/memory/ "Memory - OpenAI Agents SDK"
[9]: https://openai.github.io/openai-agents-python/ref/stream_events/ "Streaming events - OpenAI Agents SDK"


---

What is the difference between google ADK's tools and OpenAI Agent's python SDK tools?

---


Below is a clean, side‑by‑side view of **Google’s Agent Development Kit (ADK) “tools”** versus **OpenAI Agents Python SDK “tools.”** I’m assuming you mean ADK’s Python flavor and OpenAI’s *Agents SDK* (not the older Assistants API). Goal: highlight the model, how you define/host tools, orchestration primitives, and notable constraints—so you can pick the right abstraction for your build.

---

## 1) Clarify

* **Goal:** Compare “tools” between **Google ADK** and **OpenAI Agents (Python SDK)** at the design/usage level.
* **Inputs/constraints:** None provided. I’ll use vendor docs only; call out anything that’s temporally sensitive or has caveats.
* **Success metrics:** A tight diff table + practical takeaways (built‑ins, composition limits, context/state, long‑running support, auth, interop) with citations to official docs.

**Assumptions (high confidence):**

* “Google ADK” = Google’s **Agent Development Kit** (Python) and its tool model. ([Google GitHub][1])
* “OpenAI Agent’s python SDK tools” = OpenAI **Agents SDK (Python)** “tools” (hosted + function tools + agent-as-tool). ([OpenAI GitHub][2])

No questions needed.

---

## 2) Decompose → Sub‑questions answered

### A. What *is* a “tool” in each?

* **ADK:** A modular capability (function/method/another agent) used by an LLM agent. ADK has **Function Tools**, **Long‑Running Function Tools**, and **Agent‑as‑a‑Tool**. ([Google GitHub][3])
* **OpenAI Agents SDK:** Three classes—**Hosted tools** (run alongside the model, e.g., web search, file search, computer use), **Function tools** (any Python function), and **Agents as tools**. ([OpenAI GitHub][2])

### B. How are tools defined and typed?

* **ADK:** Introspects Python signatures and docstrings to build the schema; *recommends/normalizes dict outputs* (non‑dict returns are wrapped). ([Google GitHub][4])
* **OpenAI Agents:** Auto‑generates JSON schema from Python signatures/docstrings via `inspect` + Pydantic; custom `FunctionTool`’s `on_invoke_tool` **must return a string**. ([OpenAI GitHub][2])

### C. Built‑ins (what you get out of the box)?

* **ADK built‑ins:** Google Search grounding (Gemini 2 only), Code Execution, GKE code executor, Vertex AI Search, BigQuery—**but with important composition limits** (see next row). ([Google GitHub][5])
* **OpenAI built‑ins (hosted tools):** WebSearch, FileSearch (OpenAI Vector Stores), ComputerTool (Operator), CodeInterpreter, Hosted MCP, ImageGeneration, plus LocalShell (runs locally). You can define multiple hosted tools on the same agent. ([OpenAI GitHub][2])

### D. Can I mix built‑ins with other tools?

* **ADK:** **Limit today**—per root/single agent, **only one built‑in tool** and **cannot use built‑ins in sub‑agents**; you can combine via multiple agents and agent‑as‑tool instead. ([Google GitHub][5])
* **OpenAI Agents:** Examples show **multiple hosted tools together** (e.g., WebSearch + FileSearch) alongside function tools. ([OpenAI GitHub][2])

### E. “Context” passed into tools (state, artifacts, flow‑control)?

* **ADK ToolContext:** First‑class **session state** with namespaced keys (`app:*`, `user:*`, session, `temp:*`), **artifact** and **memory** services, **auth hooks**, and **post‑tool flow controls** (`skip_summarization`, `transfer_to_agent`, `escalate`). ([Google GitHub][3])
* **OpenAI Agents:** Optional `RunContextWrapper` gives you app‑defined context; **session memory** exists in the SDK (e.g., `SQLiteSession`) but artifact/memory/auth are not baked into a tool context API the way ADK does. ([OpenAI GitHub][2])

### F. Long‑running work & pause/resume

* **ADK:** **LongRunningFunctionTool** is a first‑class tool type—initiate work, send **intermediate updates**, and **pause/resume** the agent run until final result. ([Google GitHub][4])
* **OpenAI Agents:** Tool calls stream events; “long‑running” is handled at the **run/workflow** layer (e.g., Temporal integration, human‑in‑the‑loop patterns), not as a dedicated **long‑running tool type**. ([OpenAI GitHub][6])

### G. Interop with external systems (OpenAPI/MCP/etc.)

* **ADK:** **OpenAPIToolset** auto‑generates `RestApiTool`s from an OpenAPI spec; also has **MCPToolset** to surface MCP servers’ tools as native ADK tools. ([Google GitHub][7])
* **OpenAI Agents:** Built‑in **HostedMCPTool** to expose remote MCP servers; no built‑in OpenAPI‑to‑tool generator (you’d write a function tool or use MCP that wraps your API). ([OpenAI GitHub][2])

### H. Authentication inside tools

* **ADK:** ToolContext supports **auth flows**: `auth_response`, `request_credential(auth_config)`, and docs show how auth ties into `RestApiTool`/OpenAPIToolset & Google APIs. ([Google GitHub][3])
* **OpenAI Agents:** Auth is app‑level—you pass credentials into your function tools or configure hosted tool credentials; no built‑in ToolContext auth flow like ADK’s. (Docs emphasize schema/contexts; auth flow is your code.) ([OpenAI GitHub][2])

### I. “Agents as tools”

* **Both** support turning an agent into a callable **tool** (agent‑as‑tool pattern). ([Google GitHub][4], [OpenAI GitHub][2])

---

## 3) Evidence (inline)

* ADK tools overview & types (Function, Long‑Running, Agent‑as‑Tool). ([Google GitHub][3])
* ADK built‑ins + **composition limits** (one built‑in per agent; not allowed in sub‑agents). ([Google GitHub][5])
* ADK ToolContext: **state**, **artifacts**, **memory**, **flow control**; **auth hooks**. ([Google GitHub][3])
* ADK OpenAPI/MCP toolsets. ([Google GitHub][7])
* OpenAI Agents tools: hosted tools list; function tools auto‑schema; `on_invoke_tool` returns **string**; agents‑as‑tool; conditional enabling. ([OpenAI GitHub][2])
* OpenAI Agents **Memory/Session** concept. ([OpenAI GitHub][8])
* OpenAI Agents long‑running guidance is at run/workflow layer (Temporal/HITL). ([OpenAI GitHub][6])

---

## 4) Plan → Step → Progress

**Plan:**

* Compile a concise diff table across nine dimensions; surface sharp “gotchas”; include doc links.

**Step — Execution (artifact):**

### Quick diff (you can skim)

| Dimension               | Google ADK                                                                                                                                                                                       | OpenAI Agents (Python SDK)                                                                                                                                    |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Tool categories         | Function Tools, **LongRunningFunctionTool**, Agent‑as‑Tool. ([Google GitHub][4])                                                                                                                 | **Hosted tools**, Function tools, Agents as tools. ([OpenAI GitHub][2])                                                                                       |
| Define a tool           | Introspects function signature & docstring; return ideally **dict** (non‑dict is wrapped). ([Google GitHub][4])                                                                                  | Auto‑schema from signature/docstring; custom `FunctionTool.on_invoke_tool` returns **string**. ([OpenAI GitHub][2])                                           |
| Built‑ins               | Google Search, Code Execution, **GKE executor**, Vertex AI Search, **BigQuery**. **Limit: only one built‑in per (root/single) agent; built‑ins not allowed in sub‑agents.** ([Google GitHub][5]) | WebSearch, FileSearch (Vector Stores), ComputerTool, CodeInterpreter, Hosted MCP, ImageGeneration, LocalShell. Can combine in one agent. ([OpenAI GitHub][2]) |
| Composition             | Built‑in(s) constrained; combine via multiple agents + agent‑as‑tool. ([Google GitHub][5])                                                                                                       | Typical to mix **multiple** hosted tools + function tools in one agent. ([OpenAI GitHub][2])                                                                  |
| Context passed to tools | **ToolContext** gives session **state** (with prefixes), **artifacts**, **memory**, **auth**, and **flow control** (`skip_summarization`, `transfer_to_agent`, `escalate`). ([Google GitHub][3]) | Optional `RunContextWrapper` (you define); SDK offers session **memory**, but artifacts/auth/flow‑control are app‑level concerns. ([OpenAI GitHub][8])        |
| Long‑running            | **First‑class**: LongRunningFunctionTool with **intermediate/final updates**; agent runs can pause/resume. ([Google GitHub][4])                                                                  | Handled at **workflow layer** (e.g., Temporal, human‑in‑the‑loop); tool itself is not a special long‑running type. ([OpenAI GitHub][6])                       |
| OpenAPI/MCP             | **OpenAPIToolset** → many `RestApiTool`s from your spec; **MCPToolset** to surface MCP tools natively. ([Google GitHub][7])                                                                      | **HostedMCPTool** (remote MCP servers); no built‑in OpenAPI→tool generator. ([OpenAI GitHub][2])                                                              |
| Authentication          | Built‑in **auth flow hooks** in ToolContext (`request_credential`, etc.); tool docs show config patterns. ([Google GitHub][3])                                                                   | You manage creds in your code or hosted tool setup; no ToolContext auth API. ([OpenAI GitHub][2])                                                             |
| Agents as tools         | Supported (AgentTool). ([Google GitHub][4])                                                                                                                                                      | Supported (`agent.as_tool`). ([OpenAI GitHub][2])                                                                                                             |

**Progress:** Compared the abstractions, constraints, and interop; flagged where each shines, with doc anchors.

---

## 5) Define (formal-ish)

* **ADK Function Tool:** A Python function `f(a: int, b: int, tool_context: ToolContext) -> dict` whose signature/docstring are introspected to a JSON schema the LLM can call. Outputs are dict‑shaped for the agent’s “observation”; the `ToolContext` offers state/artifacts/memory/auth/flow controls. ([Google GitHub][4])
* **ADK LongRunningFunctionTool:** A wrapper around a function that kicks off work and lets the agent **pause**; the client later **continues** the run with intermediate/final results, which the framework packages back to the LLM. ([Google GitHub][4])
* **OpenAI Function Tool:** A Python function—decorated or a `FunctionTool`—with auto‑schema; custom `on_invoke_tool(ctx, args_json)` **returns a string**. Hosted tools run server‑side (except LocalShell which runs locally). ([OpenAI GitHub][2])

---

## 6) Math/Logic

N/A (no arithmetic here).

---

## 7) Algorithms/Code (minimal examples)

* **ADK (Function Tool):** `def add(a: int, b: int, tool_context: ToolContext) -> dict: return {"sum": a+b}` (introspection + dict output). ([Google GitHub][4])
* **OpenAI (Function Tool):** `@function_tool def add(a: int, b: int) -> str: return str(a+b)` or `FunctionTool(on_invoke_tool=...)` (string output from the tool invocation). ([OpenAI GitHub][2])

---

## 8) Tools (meta)

* **One tool used here:** web.run to pull **official** ADK and OpenAI Agents SDK docs; this matters because both stacks are moving targets and the limits (e.g., ADK built‑ins composition) are version‑sensitive. ([Google GitHub][5], [OpenAI GitHub][2])

---

## 9) Practical takeaways

* **Need a built‑in OpenAPI→tool bridge?** ADK’s **OpenAPIToolset** is turnkey; Agents SDK will need your own function tools or an MCP server that wraps your API. ([Google GitHub][7], [OpenAI GitHub][2])
* **Need durable, pause/resume tooling with status updates?** ADK’s **LongRunningFunctionTool** is native. OpenAI leans on **workflow/run orchestration** (e.g., Temporal) rather than a special tool type. ([Google GitHub][4], [OpenAI GitHub][6])
* **Want multiple built‑ins in one agent (search + file search + computer use)?** OpenAI SDK supports that; ADK’s built‑ins are **one per agent** and **not in sub‑agents** right now. Design around it with agent‑as‑tool if you need both. ([OpenAI GitHub][2], [Google GitHub][5])
* **Prefer richer per‑tool context primitives (state/artifacts/memory/auth/flow)?** ADK’s **ToolContext** is opinionated and full‑featured. OpenAI’s `RunContextWrapper` is flexible but you wire most services yourself. ([Google GitHub][3], [OpenAI GitHub][2])

---

## 10) Quality: pitfalls, risks, tests

* **Pitfalls**

  * **ADK built‑in tool limits** surprise teams when they try to mix search + code execution in one agent; split into sub‑agents & compose with agent‑as‑tool. Validate this early. ([Google GitHub][5])
  * **Return‑type mismatches:** ADK expects dict‑like outputs; OpenAI function tools often return strings. Standardize adapters to keep traces/readability clean. ([Google GitHub][3], [OpenAI GitHub][2])
  * **Auth & secrets:** ADK’s ToolContext can request credentials; in OpenAI, handle credentials in your function/hosted tool config. Test secure handling either way. ([Google GitHub][3])

* **Acceptance checks**

  * You can register a function tool in each stack and see the **auto‑generated schema** (types & arg descriptions) in logs/trace. ([Google GitHub][4], [OpenAI GitHub][2])
  * In ADK, call a **LongRunningFunctionTool** and verify intermediate updates and paused run; in OpenAI, verify **streaming events** and (optionally) a Temporal workflow for long tasks. ([Google GitHub][4], [OpenAI GitHub][9])
  * In ADK, try to add two built‑ins to one agent and confirm the documented constraint triggers; in OpenAI, run with WebSearch + FileSearch together. ([Google GitHub][5], [OpenAI GitHub][2])

**Log (decisions):**

* Treated “tools” as first‑class ADK vs Agents SDK concept; privileged official docs; highlighted hard constraints.

---

## Next steps (pick one)

* If you plan to **wrap a REST estate fast**, pilot ADK’s **OpenAPIToolset** on one service and measure tool‑call accuracy and schema coverage. ([Google GitHub][7])
* If you want **one agent with multiple hosted skills** (search + vector + computer use), prototype in OpenAI Agents using **two hosted tools + one function tool** and inspect traces. ([OpenAI GitHub][2])
* If your flows are **approval‑ or SLA‑bound**, run ADK’s **LongRunningFunctionTool** sample and compare with an OpenAI **Temporal** workflow for equivalent latency/observability. ([Google GitHub][4], [OpenAI GitHub][6])

---

## Open questions

* Are you optimizing for **rapid API surface ingestion** (OpenAPI) or **one‑agent multi‑capability** with minimal constraints?
* Do you need **durable long‑running** tasks inside the tool abstraction itself, or is **workflow‑level** durability okay?

---

## Risks & mitigations

* **Docs are moving:** Re‑check ADK built‑in composition limits and tool lists before locking architecture. (Mitigate with a spike and CI checks against templates.) ([Google GitHub][5])
* **Vendor coupling:** ADK’s Google Search & BigQuery tools tie you to Google infra; OpenAI’s hosted tools tie you to OpenAI Vector Stores/Operator. Keep function tools for portability. ([Google GitHub][5], [OpenAI GitHub][2])

---

### Bottom line (one‑liner)

* **ADK** gives you **strong per‑tool context/state/auth and first‑class long‑running tools**, plus an **OpenAPI→tool** bridge—at the cost of **stricter built‑in composition** today. ([Google GitHub][4])
* **OpenAI Agents** gives you **richer hosted tool variety and easy mixing** inside one agent, with clean function‑tool ergonomics—long‑runs handled at the **workflow** level. ([OpenAI GitHub][2])

**Confidence:** High on the broad differences; medium on fast‑changing limits (verify on your specific versions).

[1]: https://google.github.io/adk-docs/ "Agent Development Kit"
[2]: https://openai.github.io/openai-agents-python/tools/ "Tools - OpenAI Agents SDK"
[3]: https://google.github.io/adk-docs/tools/ "Tools - Agent Development Kit"
[4]: https://google.github.io/adk-docs/tools/function-tools/ "Function tools - Agent Development Kit"
[5]: https://google.github.io/adk-docs/tools/built-in-tools/ "Built-in tools - Agent Development Kit"
[6]: https://openai.github.io/openai-agents-python/running_agents/?utm_source=chatgpt.com "Running agents - OpenAI Agents SDK"
[7]: https://google.github.io/adk-docs/tools/openapi-tools/?utm_source=chatgpt.com "OpenAPI tools - Agent Development Kit - Google"
[8]: https://openai.github.io/openai-agents-python/ref/memory/ "Memory - OpenAI Agents SDK"
[9]: https://openai.github.io/openai-agents-python/ref/stream_events/ "Streaming events - OpenAI Agents SDK"



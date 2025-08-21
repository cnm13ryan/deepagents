# Agent Framework Tools: A Unified Comparison

## Executive Summary

This document compares how four major agent frameworks conceptualize and implement "tools" - the mechanisms that allow AI agents to interact with external systems and perform actions beyond text generation.

**Bottom Line Up Front:**
- **Inspect-AI**: Evaluation-focused with built-in sandboxing and approval workflows
- **LangChain**: Application-oriented with broad ecosystem integrations  
- **OpenAI Agents SDK**: Production runtime with hosted capabilities and workflow orchestration
- **Google ADK**: Rich context management with strong auth flows but composition constraints

---

## Framework Overview

| Framework | Owner | Primary Purpose | Tool Philosophy |
|-----------|-------|-----------------|-----------------|
| **Inspect-AI** | UK AI Security Institute | AI model evaluation & benchmarking | Tools expand model capabilities during controlled test runs with safety guardrails |
| **LangChain** | LangChain AI | General agent applications | Tools are composable building blocks for reasoning chains and graphs |
| **OpenAI Agents SDK** | OpenAI | Production agentic workflows | Tools enable work execution through hosted capabilities and custom functions |
| **Google ADK** | Google | Enterprise agent development | Tools are contextually-aware capabilities with rich state management |

---

## Core Tool Comparison Matrix

| Dimension | Inspect-AI | LangChain | OpenAI Agents SDK | Google ADK |
|-----------|------------|-----------|------------------|------------|
| **Tool Definition** | `@tool` decorator with async `execute()` function | `@tool` decorator or `StructuredTool` with Runnable interface | `@function_tool` or `FunctionTool` class; hosted tools via API | Function with `ToolContext` parameter; auto-schema from signature |
| **Return Types** | Any Python type | Any Python type | **String required** for function tools | **Dict preferred** (non-dict wrapped) |
| **Built-in Tools** | web_search, bash, python, web_browser, computer, text_editor, think | Community ecosystem via integrations | WebSearch, FileSearch, ComputerTool, CodeInterpreter, ImageGeneration | Google Search, Code Execution, GKE executor, Vertex AI Search, BigQuery |
| **Tool Composition** | ✅ Flexible mixing of tools | ✅ Flexible mixing of tools | ✅ Multiple hosted + function tools | ⚠️ **One built-in per agent**; no built-ins in sub-agents |
| **Execution Environment** | Local or Docker sandboxes with resource limits | Local execution (no built-in sandbox) | Hosted tools on OpenAI infra; function tools locally | Local execution with optional sandboxing |
| **Context/State** | Tool-specific parameters only | Optional context via chains/graphs | Optional `RunContextWrapper`; session memory | **Rich `ToolContext`**: state, artifacts, memory, auth, flow control |
| **Long-running Support** | Standard async execution | Handled via workflow orchestration | Workflow-level (Temporal, streaming) | **First-class `LongRunningFunctionTool`** with pause/resume |
| **Authentication** | Manual credential handling | Manual credential handling | App-level credential management | **Built-in auth flows** in ToolContext |
| **MCP Support** | ✅ Native MCP server integration | ❌ Not a core primitive | ✅ HostedMCPTool for remote servers | ✅ MCPToolset for native integration |
| **OpenAPI Integration** | Manual function wrapping | Manual function wrapping | Manual function wrapping or MCP | **Auto-generation via OpenAPIToolset** |
| **Sandboxing/Security** | **First-class Docker/K8s/VM isolation** | No built-in sandbox | Hosted tools isolated; function tools run locally | Optional containerization |
| **Human Approval** | **Built-in approval policies** per tool/action | Custom implementation patterns | Custom workflow patterns | Flow control via ToolContext |
| **Observability** | Rich eval logs with VS Code viewer | LangSmith tracing (opt-in) | Built-in tracing with pluggable processors | Standard logging with tool context |

---

## Tool Categories by Framework

### Inspect-AI Tools
- **Standard Tools**: web_search, bash, python, bash_session, text_editor, web_browser, computer, think
- **MCP Tools**: Any MCP server tools (local, HTTP, sandbox execution)
- **Custom Tools**: User-defined functions with `@tool` decorator

### LangChain Tools  
- **Core Tools**: Basic schema + executor pattern
- **Integration Tools**: Large ecosystem (search, retrievers, APIs, databases)
- **Custom Tools**: `@tool` decorator or `StructuredTool` class

### OpenAI Agents SDK Tools
- **Hosted Tools**: WebSearchTool, FileSearchTool, ComputerTool, CodeInterpreterTool, HostedMCPTool, ImageGenerationTool
- **Function Tools**: Custom Python functions with auto-schema
- **Agent Tools**: Nested agents exposed as tools
- **Local Tools**: LocalShellTool (runs in local environment)

### Google ADK Tools
- **Function Tools**: Standard Python functions with ToolContext
- **Long-Running Tools**: Asynchronous tools with intermediate updates
- **Built-in Tools**: Google Search, Code Execution, GKE executor, Vertex AI Search, BigQuery
- **Generated Tools**: Auto-generated from OpenAPI specs
- **MCP Tools**: Native MCP server integration
- **Agent Tools**: Sub-agents exposed as tools

---

## Key Architectural Differences

### Security & Isolation Model

| Framework | Approach | Strengths | Limitations |
|-----------|----------|-----------|-------------|
| **Inspect-AI** | **Built-in sandboxing** with Docker/K8s containers, resource limits, per-sample isolation | Strong security for untrusted code execution; eval reproducibility | Additional infrastructure complexity |
| **LangChain** | **No built-in isolation** - user implements service boundaries | Maximum flexibility; simple deployment | Security is entirely user responsibility |
| **OpenAI Agents SDK** | **Hosted tool isolation** on OpenAI infrastructure; local function tools | Secure hosted capabilities; easy setup | Vendor lock-in for hosted tools |
| **Google ADK** | **Optional containerization** with ToolContext controls | Flexible security model; rich context | Less opinionated than Inspect-AI |

### State & Context Management

| Framework | State Approach | Context Richness | Persistence |
|-----------|----------------|------------------|-------------|
| **Inspect-AI** | Tool-specific parameters; eval transcripts | Basic | Eval logs and scoring |
| **LangChain** | Chain/graph-level state management | Moderate | Custom implementation |
| **OpenAI Agents SDK** | Session memory; optional context wrappers | Moderate | Built-in session storage |
| **Google ADK** | **Rich ToolContext** with namespaced state (`app:*`, `user:*`, `temp:*`) | **Highest** | Built-in artifacts and memory services |

### Long-Running Operations

| Framework | Approach | Capabilities | Use Cases |
|-----------|----------|--------------|-----------|
| **Inspect-AI** | Standard async patterns | Basic async execution | Short to medium eval tasks |
| **LangChain** | Workflow orchestration (external) | Depends on integration | Complex multi-step processes |
| **OpenAI Agents SDK** | Workflow-level with Temporal/streaming | Sophisticated orchestration | Production workflows |
| **Google ADK** | **First-class LongRunningFunctionTool** | Pause/resume with intermediate updates | Approval workflows, long-running tasks |

---

## Framework Selection Guide

### Choose **Inspect-AI** when:
- Building AI model evaluation harnesses
- Need reproducible, controlled testing environments  
- Require built-in sandboxing for untrusted code execution
- Want comprehensive eval logging and scoring
- Focus on model capability assessment rather than production deployment

### Choose **LangChain** when:
- Building general-purpose AI applications
- Need maximum ecosystem flexibility and integrations
- Want to compose tools into complex reasoning chains
- Have custom security/deployment requirements
- Prefer community-driven tool ecosystem

### Choose **OpenAI Agents SDK** when:
- Building production agentic workflows
- Want hosted capabilities (web search, computer use, file search)
- Need sophisticated session management and tracing
- Building on OpenAI model infrastructure
- Require robust workflow orchestration patterns

### Choose **Google ADK** when:
- Need rich contextual state management across tools
- Require built-in authentication flows and credential management
- Want first-class long-running tool support with pause/resume
- Need rapid API integration via OpenAPI specs
- Building enterprise agents with complex state requirements
- **Note**: Currently limited to one built-in tool per agent

---

## Tool Composition Patterns

### Multi-Tool Workflows

```
Inspect-AI:     [web_search] + [python] + [text_editor] → eval_result
LangChain:      [search] + [retriever] + [calculator] → chain_output  
OpenAI Agents:  [WebSearch] + [FileSearch] + [CodeInterpreter] → agent_response
Google ADK:     [RestApiTool] + [LongRunningTool] → context_aware_result
```

### Composition Constraints

| Framework | Flexibility | Constraints |
|-----------|-------------|-------------|
| **Inspect-AI** | High | None significant |
| **LangChain** | High | None significant |  
| **OpenAI Agents SDK** | High | None significant |
| **Google ADK** | **Limited** | Only one built-in tool per root agent; no built-ins in sub-agents |

---

## Integration & Interoperability

### MCP (Model Context Protocol) Support

| Framework | MCP Integration | Capabilities |
|-----------|-----------------|--------------|
| **Inspect-AI** | ✅ **Native support** | Local, HTTP, and sandbox MCP servers; remote execution via providers |
| **LangChain** | ❌ **Not core** | Can integrate external services as tools, but MCP isn't first-class |
| **OpenAI Agents SDK** | ✅ **HostedMCPTool** | Remote MCP servers with filtering and caching |
| **Google ADK** | ✅ **MCPToolset** | Native MCP server integration as ADK tools |

### OpenAPI Integration

| Framework | OpenAPI Support | Implementation |
|-----------|-----------------|----------------|
| **Inspect-AI** | Manual | Write custom functions to wrap APIs |
| **LangChain** | Manual | Custom tool creation or MCP wrapping |
| **OpenAI Agents SDK** | Manual | Function tools or MCP servers |
| **Google ADK** | ✅ **Auto-generation** | **OpenAPIToolset** creates RestApiTools from specs |

---

## Code Examples

### Basic Tool Definition

#### Inspect-AI
```python
from inspect_ai.tool import tool

@tool
def add():
    async def execute(x: int, y: int):
        """Add two numbers."""
        return x + y
    return execute
```

#### LangChain  
```python
from langchain_core.tools import tool

@tool
def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b
```

#### OpenAI Agents SDK
```python
from agents import function_tool

@function_tool
def calculate(a: int, b: int) -> str:
    """Calculate sum of two numbers."""
    return str(a + b)
```

#### Google ADK
```python
from adk import Agent
from adk.tools import ToolContext

def add_numbers(a: int, b: int, tool_context: ToolContext) -> dict:
    """Add two numbers with context."""
    return {"sum": a + b, "operation": "addition"}
```

---

## Migration Considerations

### From LangChain to Inspect-AI
- **Pros**: Gain evaluation focus, built-in sandboxing, approval workflows
- **Cons**: Lose broad ecosystem; need to adapt application-focused patterns
- **Effort**: Medium - conceptual shift from apps to evals

### From OpenAI Agents to Google ADK  
- **Pros**: Gain richer context management, auth flows, OpenAPI auto-generation
- **Cons**: Lose multiple built-in tool composition; vendor lock-in shift
- **Effort**: Medium - tool context refactoring required

### From Inspect-AI to OpenAI Agents
- **Pros**: Gain production runtime features, hosted tools, workflow orchestration
- **Cons**: Lose evaluation focus, built-in sandboxing, approval workflows  
- **Effort**: High - fundamental purpose shift from eval to production

---

## Future Trends & Considerations

### Standardization
- **MCP adoption**: Growing support across frameworks for tool interoperability
- **Tool composition**: Movement toward more flexible multi-tool workflows
- **Security models**: Increasing focus on sandboxing and approval patterns

### Vendor Considerations
- **OpenAI Agents SDK**: Hosted tools create vendor dependencies but reduce infrastructure burden
- **Google ADK**: Strong integration with Google Cloud ecosystem
- **Inspect-AI**: Open source with academic/research focus
- **LangChain**: Community-driven with broad provider support

### Technical Debt Risks
- **Tool sprawl**: Too many tools can harm model selection performance
- **Context complexity**: Rich context systems (ADK) can become complex to manage
- **Security boundaries**: Manual security approaches (LangChain) require careful architecture

---

## Conclusion

Each framework reflects different philosophies about agent tool usage:

- **Inspect-AI** prioritizes **safety and reproducibility** for evaluation scenarios
- **LangChain** emphasizes **flexibility and ecosystem breadth** for diverse applications  
- **OpenAI Agents SDK** focuses on **production readiness** with hosted capabilities
- **Google ADK** provides **enterprise-grade context management** with some composition trade-offs

The choice depends on your primary use case: evaluation harnesses, flexible applications, production workflows, or enterprise agent development with rich state management requirements.

# HybridAgent Framework: Blending Inspect-AI Safety with LangChain Flexibility

## Design Philosophy: "Fast Iteration with Safety Guardrails"

The framework combines the **safety-first approach of Inspect-AI** with the **flexible orchestration power of LangChain** to create an agentic system that adapts to your needs - from rapid prototyping to production deployment.

## Key Innovations

### 🛡️ **Adaptive Safety Levels**
Tools automatically determine their execution mode based on safety classification:

```python
# Safe tools execute locally for speed
web_search = HybridWebSearch()  # ToolSafetyLevel.SAFE → Local execution

# Dangerous tools execute in sandboxes
python_with_network = HybridPythonExecutor(allow_network=True)  # → Sandboxed

# Critical tools require approval
file_system = HybridFileSystem()  # ToolSafetyLevel.CRITICAL → Approval + Sandbox
```

### 🔄 **Context-Aware Execution Modes**
Single tools can execute differently based on context:

```python
tool.execution_mode = ExecutionMode.LOCAL          # Fast prototyping
tool.execution_mode = ExecutionMode.SANDBOXED      # Safe evaluation  
tool.execution_mode = ExecutionMode.APPROVAL       # Human oversight
tool.execution_mode = ExecutionMode.GRAPH          # Complex orchestration
```

### 🎯 **Use Case Configurations**
Framework adapts behavior for different scenarios:

```python
# Fast prototyping: Local execution, no approvals
agent = create_agent_for_use_case("prototyping", tools)

# Production: Sandboxed execution, approvals for critical tools
agent = create_agent_for_use_case("production", tools) 

# Evaluation: Full logging, sandboxing, detailed reports
agent = create_agent_for_use_case("evaluation", tools)
```

## Core Strengths Inherited

### From **Inspect-AI** 🛡️:
- **Sandboxed execution** with Docker containers and resource limits
- **Human approval workflows** for dangerous operations
- **Rich logging and evaluation** with detailed execution traces
- **Safety-first design** with automatic threat classification
- **Per-session isolation** for multi-tenant scenarios

### From **LangChain** 🔗:
- **Flexible tool composition** with no artificial limits
- **LangGraph workflow orchestration** for complex multi-step tasks
- **Broad ecosystem compatibility** - can wrap any LangChain tool
- **Conditional routing** and dynamic workflow construction
- **Agent memory and state management** across conversations

## Novel Hybrid Capabilities

### 🎛️ **Dynamic Safety Escalation**
```python
# Tool starts local for speed, escalates to sandbox if needed
if detect_dangerous_pattern(code):
    context.execution_mode = ExecutionMode.SANDBOXED
    context.requires_approval = True
```

### 📊 **Real-time Observability**
```python
# Combines Inspect-AI's detailed logging with LangGraph's workflow visibility
execution_trace = [
    {"tool": "web_search", "mode": "local", "duration": 0.5},
    {"tool": "python_executor", "mode": "sandboxed", "duration": 2.1, "approval": True}
]
```

### 🔧 **Ecosystem Bridge**
```python
# Any tool can be converted to either framework's interface
hybrid_tool.to_langchain_tool()  # For LangChain compatibility
hybrid_tool.to_inspect_tool()    # For Inspect-AI evaluations
```

## Solving the Fast Prototyping Problem

### ⚡ **Iteration Speed**
- **Local execution by default** for safe tools (web search, read-only operations)
- **No setup overhead** - tools work immediately without external dependencies
- **Gradual safety escalation** - only sandbox when necessary

### 🛡️ **Safety When Needed**
- **Automatic sandboxing** for dangerous operations (code execution, file system)
- **Human approval gates** for critical operations
- **Resource limits** prevent runaway processes

### 📈 **Production Readiness**
- **Same codebase** scales from prototype to production
- **Configuration-driven safety** - change settings, not code
- **Full audit trails** for compliance and debugging

## Usage Patterns

### **Pattern 1: Progressive Safety**
```python
# Start fast and safe
agent = HybridAgent(tools=[web_search, read_only_tools])

# Add moderate capabilities  
agent.add_tool(HybridPythonExecutor(allow_network=False))

# Scale to full capabilities with safety
agent.add_tool(HybridPythonExecutor(allow_network=True))  # Auto-sandboxed
```

### **Pattern 2: Context-Driven Execution**
```python
# Same tool, different safety based on content
python_tool = HybridPythonExecutor()

# Safe code → local execution
result = await python_tool.execute(context, code="print('hello')")

# Dangerous code → automatic sandbox
result = await python_tool.execute(context, code="import subprocess; subprocess.run(...)")
```

### **Pattern 3: Workflow Orchestration with Safety**
```python
workflow = HybridWorkflow("research_pipeline")

# Safe tools in parallel
workflow.add_parallel_branch([web_search, file_reader])

# Dangerous tools with approval gates
workflow.add_approval_gate(before="code_execution")
workflow.add_tool(python_executor)  # Auto-sandboxed

# Results aggregation
workflow.add_node("synthesize", synthesize_results)
```

## Framework Advantages

### 🚀 **For Fast Prototyping:**
- Zero setup time for safe operations
- Gradual capability scaling
- No external dependencies blocking iteration
- Full transparency and control

### 🏢 **For Production:**
- Enterprise-grade safety controls
- Audit trails and compliance reporting
- Human oversight for critical operations
- Scalable multi-tenant isolation

### 🔬 **For Research/Evaluation:**
- Detailed execution logging
- Reproducible sandboxed environments
- Safety incident reporting
- Performance metrics and analysis

## Implementation Philosophy

### **Safety by Design**
- Tools declare their safety level upfront
- Framework automatically applies appropriate controls
- Escalation happens transparently when needed

### **Performance by Default**
- Safe operations execute locally for speed
- Sandboxing only when necessary
- Efficient resource utilization

### **Flexibility Through Configuration**
- Same codebase adapts to different use cases
- Runtime safety level adjustment
- Pluggable execution engines

## Future Extensions

### **Advanced Safety Features:**
- ML-based threat detection in tool inputs
- Dynamic resource limit adjustment
- Cross-tool dependency analysis

### **Enhanced Orchestration:**
- Multi-agent workflows with safety isolation
- Distributed execution across secure environments
- Tool recommendation based on safety profiles

### **Ecosystem Integration:**
- Native MCP (Model Context Protocol) support
- OpenAPI auto-generation with safety classification
- Integration with external approval systems

---

## Bottom Line

The HybridAgent framework solves the fundamental tension between **speed and safety** in agent development. You get:

- **LangChain's flexibility** for rapid iteration and complex workflows
- **Inspect-AI's safety** for production deployment and evaluation
- **Unified interface** that scales from prototype to production
- **Open source tools** with configurable safety controls

This enables true **fast prototyping of Deep Agents** - you can iterate quickly on safe operations while automatically getting enterprise-grade controls when you need them.

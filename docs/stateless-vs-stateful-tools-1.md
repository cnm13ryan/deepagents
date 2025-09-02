# What is the difference between stateless and stateful tools?

Note: A canonical, harmonized guide is available at [Stateless vs Stateful Tools — Harmonized](./stateless-vs-stateful-tools-harmonized.md), which unifies Inspect AI patterns with structured API/session templates and checklists.

The difference between stateless and stateful tools in inspect_ai relates to whether tools maintain state across multiple invocations during an evaluation. <cite/>

## Stateless Tools

Stateless tools process each call independently without retaining any information between invocations. [1](#0-0)  For example, the Brave Search server is stateless because "it just processes one search at a time" without maintaining any persistent state. [1](#0-0) 

The `bash()` and `python()` tools are also stateless - each command executes in a fresh session without retaining environment variables, working directory, or command history from previous calls. [2](#0-1) 

## Stateful Tools

Stateful tools retain context and state across multiple invocations. [3](#0-2)  Examples include:

- **Knowledge Graph Memory server**: "maintains a knowledge graph in memory" [3](#0-2) 
- **`bash_session()` tool**: "retains its state across calls from the model" including "prompt, working directory, and environment variables" [4](#0-3) 
- **`web_browser()` tool**: maintains browser state, navigation history, and page context across interactions [5](#0-4) 

## Implementation Patterns

Stateful tools in inspect_ai use the `store_as()` function to maintain state across invocations. [6](#0-5)  For example, the `web_surfer()` tool demonstrates this pattern by storing message history in a `WebSurferState` model and passing an `instance` parameter to create isolated state per tool instance. [7](#0-6) 

For MCP servers specifically, stateful servers require persistent connections to maintain their state, which the `react()` agent handles automatically using the `mcp_connection()` context manager. [8](#0-7) 

## Notes

The distinction is particularly important when using Model Context Protocol (MCP) servers, as it determines whether you need persistent connections to maintain server state across tool calls. The inspect_ai framework provides built-in support for both patterns through different connection management strategies.

Wiki pages you might want to explore:
- [Agents and Tools (UKGovernmentBEIS/inspect_ai)](/wiki/UKGovernmentBEIS/inspect_ai#5)

---

# What are the considerations and best practices that one needs to be aware of when designing and building stateless tools and stateful tools respectively.

Based on the codebase context, you're asking about design considerations and best practices for building stateless versus stateful tools in the inspect_ai framework. <cite/>

## Stateless Tool Design Considerations

### Simplicity and Reliability
Stateless tools are inherently simpler to design and debug since each invocation is independent. [1](#1-0)  The `bash()` and `python()` tools exemplify this pattern - each command executes in a fresh session without retaining environment variables, working directory, or command history. [2](#1-1) 

### Error Handling
For stateless tools, you should rely on inspect_ai's default error handling which automatically manages expected errors like `TimeoutError`, `PermissionError`, and `UnicodeDecodeError`. [3](#1-2)  This reduces the complexity of your tool implementation since you don't need to manage state corruption from failed operations.

### Parallel Execution Support
Stateless tools naturally support parallel execution since there's no shared state to corrupt. [4](#1-3)  The framework checks the `parallel` attribute to determine if tools can be executed concurrently.

## Stateful Tool Design Considerations

### State Management with `store_as()`
Stateful tools must use the `store_as()` function to maintain state across invocations. [5](#1-4)  The `web_surfer()` tool demonstrates this pattern by storing message history in a `WebSurferState` model. [6](#1-5) 

### Instance Management
For stateful tools, you should provide an `instance` parameter to enable multiple isolated instances of the same tool. [7](#1-6)  This allows each tool instance to maintain separate state, as shown in the `web_surfer()` implementation where the instance is passed to both `store_as()` and the underlying `web_browser()` tool. [8](#1-7) 

### Connection Management for MCP Servers
Stateful MCP servers require persistent connections to maintain their state. [9](#1-8)  The `react()` agent automatically handles this using the `mcp_connection()` context manager, [10](#1-9)  but custom agents need to explicitly manage these connections. [11](#1-10) 

### Parallel Execution Limitations
Stateful tools often cannot support parallel execution due to state consistency concerns. [12](#1-11)  You should set `parallel=False` in the tool decorator to prevent concurrent execution that could corrupt shared state.

## Implementation Architecture Patterns

### Stateful Tool Container Design
For complex stateful tools, inspect_ai uses a container-based architecture where stateful tools maintain long-running processes via JSON RPC to HTTP server processes. [13](#1-12)  Each stateful tool should have its own subdirectory with `json_rpc_methods.py`, `tool_types.py`, and `controller.py` files to separate concerns. [14](#1-13) 

### Type Safety and Parameter Handling
Both stateless and stateful tools must provide proper type annotations for parameters. [15](#1-14)  The framework uses these annotations to validate and parse tool parameters, raising `ToolParsingError` for missing required parameters.

## Notes

The choice between stateless and stateful design significantly impacts tool complexity, error handling, and parallel execution capabilities. Stateless tools are generally preferred for their simplicity and reliability, while stateful tools are necessary when you need to maintain context across multiple invocations, such as with interactive sessions or cumulative operations.

Wiki pages you might want to explore:
- [Model System (UKGovernmentBEIS/inspect_ai)](/wiki/UKGovernmentBEIS/inspect_ai#3)



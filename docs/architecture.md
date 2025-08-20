# DeepAgents Architecture

This document explains how the DeepAgents package is structured and how a “deep” agent operates at runtime. It is based on the current repository sources and example app.

## Overview

DeepAgents augments a standard LLM tool-using loop with three key capabilities to handle longer, multi‑step tasks reliably:
- Planning: a lightweight todo tool and prompt guidance encourage explicit plans and progress tracking.
- Sub‑agents: a `task` tool spawns focused sub‑agents with their own prompts/tools (“context quarantine”).
- Sandboxed workspace: a mock, in‑memory filesystem carried in the agent state for creating and editing artifacts.

The result is packaged as a LangGraph ReAct agent, so you can stream, checkpoint, inject humans‑in‑the‑loop, and reuse standard LangGraph patterns.

## Key Modules

- `src/deepagents/graph.py`: Entry point `create_deep_agent(...)`. Wires model, prompt, and tools; returns a LangGraph ReAct agent.
- `src/deepagents/state.py`: State schema `DeepAgentState` extending LangGraph’s `AgentState` with `todos` and mock `files`.
- `src/deepagents/tools.py`: Built‑in tools: `write_todos`, `ls`, `read_file`, `write_file`, `edit_file`.
- `src/deepagents/sub_agent.py`: Builds the `task` tool; manages sub‑agent creation and integration.
- `src/deepagents/prompts.py`: Operational guidance for planning, file editing, and sub‑agent usage.
- `src/deepagents/model.py`: Default model selection via environment (Ollama or LM‑Studio); supports custom models.
- Example app: `examples/research/run_local.py` demonstrates a deep research workflow with an internet search tool and critique sub‑agent.

## Agent Construction (`create_deep_agent`)

Signature:

```
create_deep_agent(
  tools,                   # user tools (functions or LangChain tools)
  instructions: str,       # app-specific system guidance
  model=None,              # optional LangChain chat model (else default)
  subagents=None,          # optional list of SubAgent dicts
  state_schema=None,       # defaults to DeepAgentState
  config_schema=None,
  checkpointer=None        # optional LangGraph checkpointer
)
```

Behavior:
- Prompt = `instructions` + a small base prompt that reinforces planning and the `task` tool.
- Tools = user tools + built‑ins (planning + filesystem) + a generated `task` tool (see Sub‑agents below).
- Model = supplied or resolved by `get_default_model()` (see Model Selection).
- Returns a LangGraph `create_react_agent` graph configured with the above.

## State Model

`DeepAgentState` extends the standard LangGraph agent state with:
- `todos: list[Todo]` — structured plan tracking items with `pending | in_progress | completed`.
- `files: dict[str, str]` — a single‑level, in‑memory “mock filesystem,” merged via a reducer to keep updates consistent across tool calls.

This empowers the agent to both show progress and to create/edit artifacts without touching the host filesystem.

## Built‑in Tools

- `write_todos(todos) -> Command`
  - Stores a well‑formed todo list in the state and logs a tool message. Encouraged by prompts for frequent, incremental planning.

- `ls(state) -> list[str]`
  - Lists file names in the mock filesystem (`state["files"]`).

- `read_file(file_path, offset=0, limit=2000) -> str`
  - Reads from the mock filesystem and returns `cat -n`‑style text with line numbers (supports offsets/limits; long lines truncated).

- `write_file(file_path, content) -> Command`
  - Creates/overwrites a file within the mock filesystem; updates state and logs progress.

- `edit_file(file_path, old_string, new_string, replace_all=False) -> Command`
  - Exact, guard‑railed string replacement. Fails if the file is missing or `old_string` is non‑unique (unless `replace_all=True`). Prompts instruct the agent to read first and provide enough context to avoid accidental multi‑matches.

All built‑ins return `Command(update=...)` so changes merge atomically into the LangGraph state and attach a `ToolMessage` tied to the tool call id.

## Sub‑agents and the `task` Tool

The `_create_task_tool(...)` helper constructs a special `task` tool that can launch sub‑agents:
- A default `general-purpose` sub‑agent is always available, inheriting the main instructions and tools.
- You can define custom sub‑agents via dictionaries (name, description, prompt, optional `tools`, optional `model_settings`).
- When invoked with a description and `subagent_type`, the tool runs the chosen sub‑agent and returns a `Command` that:
  - Merges any files produced by the sub‑agent back into the main state.
  - Appends a `ToolMessage` containing the sub‑agent’s final content.

Rationale: “Context quarantine.” Sub‑agents can explore or perform targeted work without polluting the main chat history; only the result is imported back.

## Prompting Strategy

DeepAgents relies on operational prompting to produce “deep” behavior:
- Encourages proactive planning via `write_todos` (when/when not to use; examples).
- Teaches correct file read/edit behavior (line‑numbered reads; exact‑match edits; avoid ambiguous replacements).
- Explains sub‑agent usage via `task`, including when to delegate and how to structure requests.

Your `instructions` are combined with a small base prompt that reinforces these behaviors.

## Model Selection

The default model is selected by environment variables:
- `DEEPAGENTS_MODEL_PROVIDER=ollama` (default): uses `langchain_ollama.ChatOllama` with `OLLAMA_MODEL_NAME` and optional `OLLAMA_BASE_URL/OLLAMA_HOST`.
- `DEEPAGENTS_MODEL_PROVIDER=lm-studio`: uses `langchain_openai.ChatOpenAI` pointed at LM‑Studio’s OpenAI‑compatible endpoint (`LM_STUDIO_BASE_URL`, `LM_STUDIO_MODEL_NAME`, `LM_STUDIO_API_KEY`).

You may also pass any LangChain chat model instance directly. Per‑sub‑agent overrides are supported through `model_settings`.

## Execution Flow

1) Input: `agent.invoke({"messages": [{"role": "user", "content": "..."}]})`.
2) ReAct loop chooses between tools and direct responses:
   - Plan with `write_todos`; keep one task `in_progress` at a time.
   - Read/write/edit artifacts in the mock filesystem.
   - Delegate complex sub‑problems to `task` sub‑agents; merge results back.
3) Output: the final assistant message and any `files` accumulated in state (you can also seed initial `files` in the input state).

## Example: Deep Research Agent

The example app (`examples/research/run_local.py`) demonstrates a pattern:
- Adds an optional `internet_search` tool (Tavily; degrades gracefully when not configured).
- Orchestrates research by spawning one or more research sub‑agents via `task`.
- Writes a comprehensive `final_report.md` and can call a critique sub‑agent to iterate.
- Runs locally via CLI or LangGraph Studio; includes robust model selection helpers.

## Notes & Constraints

- Mock filesystem is flat (no subdirectories); designed for isolation and parallelism without touching the host FS.
- `edit_file` is intentionally strict for determinism; provide sufficient context or use `replace_all` deliberately.
- Because the agent is a LangGraph graph, you can layer in checkpointing, human approvals, streaming, and memory using standard LangGraph features.


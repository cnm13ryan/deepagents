---
title: Detailed Architecture
---

# Architecture (Detailed)

This expands on the high‑level picture in `README.md` with tool modes, state, and filesystem behavior. Rendered by GitHub or any Markdown renderer with Mermaid enabled.

```mermaid
flowchart LR
  %% Legend: solid = control/invocation, dashed = data/outputs

  SP[[System Prompt / Config]] -->|instantiate • steer| A["Supervisor (react)"]
  MR["Model Resolver<br/>(provider/role env)"] -->|configure| A
  A -->|output & events| LT["Logs/Traces<br/>(transcript • trace.log)"]

  %% ───── Tool mode (single‑shot) ─────
  A -->|tool call| G{"Approvals & Policies<br/>(init_tool_approval) • optional"}

  subgraph Tools["Tools (single‑shot)"]
    direction TB

    subgraph StatelessTools["Stateless Tools"]
      direction TB
      THP[Todos & Plan<br/>write_todos • update_todo_status]
      THK["think<br/>(default on)"]
      WS[web_search]
      BSH[bash]
      PY[python]
      FST[FS Tools]
    end

    subgraph StatefulTools["Stateful Tools (opt‑in)"]
      direction TB
      WB[web_browser]
      BSS[bash_session]
    end

    subgraph FSpath[File‑System Paths]
      direction TB
      VFS[(Virtual Files Store)]
      SBX[["Sandboxed Editor<br/>(via text_editor)"]]
      HFS[(Host FS)]
      FST -->|default| VFS
      FST -->|"INSPECT_AGENTS_FS_MODE=sandbox"| SBX
      SBX --> HFS
      %% note: delete disabled in sandbox
    end
  end

  G -->|approved| THP & THK & WS & BSH & PY & FST & WB & BSS
  THP -.->|result| A
  THK -.->|result| A
  WS  -.->|result| A
  BSH -.->|result| A
  PY  -.->|result| A
  FST -.->|result| A
  WB  -.->|result| A
  BSS -.->|result| A

  %% ───── Handoff mode (iterative) ─────
  A -->|handoff| CG{"Context Gate<br/>input_filter: strict | scoped<br/>output_filter<br/>limits: time • messages • tokens<br/>(per‑agent env overrides)"}
  subgraph SAGroup["Sub‑Agents (iterative control)"]
    direction TB
    SAP[[Sub‑Agent Prompt]]
    SA[Sub‑Agents]
    SAP --> SA
  end
  CG <-->|"handoff (iterative)"| SA
  SA -.->|updates • returns| A
```

## Notes
- Keep this as the single source for the detailed diagram. Link here from `README.md` to avoid duplication.
- If your docs site doesn’t render Mermaid, export a PNG/SVG from this source and store under `docs/diagrams/` alongside the `.mmd` source.

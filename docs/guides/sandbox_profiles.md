# Sandboxing Profiles for Agentic Evaluations (aligned with AISI guidance)

This document describes how to select and configure sandboxing for agentic evaluations using Inspect + `inspect_agents`, aligning to AISI’s “Technical guidance: sandboxing configurations for agentic evaluations”. See the full PDF under `docs/reference/Technical_Guidance_on_SandBoxing.pdf`.

## Overview

Sandboxing is defined across three independent dimensions. Choose a profile in the form `Tx.Hx.Nx` for each evaluation and record it in your run metadata.

- T — Tooling: the agent’s execution + browser capabilities
- H — Host Isolation: where/how tools execute (process/container/VM)
- N — Network Isolation: allowed egress to the internet

Typical profiles:
- T2.H1.N2 — Text-only, containerized, fully offline
- T1.H1.N1 — Web-only (restricted domains), containerized
- T0.H2.N1 — Code execution allowed, remote containers, restricted egress
- T0.H3.N2 — Code execution with strong isolation (VM) and no external network

## Dimension definitions

- T0: Unrestricted execution (e.g., bash/python) and optional browser
- T1: Restricted execution (web search/browse + basic, no arbitrary code)
- T2: No execution (pure text generation)

- H0: No isolation (local process on host)
- H1: Local containerization (Docker / Compose)
- H2: Remote containerization (Kubernetes pods)
- H3: Remote VM isolation (e.g., Proxmox)

- N0: Full external network access
- N1: Allow-listed domains/APIs only
- N2: No external network (local comms only if required)

## Mapping profiles to Inspect + `inspect_agents`

The `Task(..., sandbox=...)` parameter selects host isolation. Tooling is controlled by `inspect_agents.tools.standard_tools()` via environment flags. Network isolation is applied by the sandbox provider (prefer K8s for N1/N2).

- Tooling (T):
  - T2: Do not enable tools; use `solver=[generate()]`.
  - T1: Enable only web tools: set `INSPECT_ENABLE_WEB_SEARCH=1`; do not set `INSPECT_ENABLE_EXEC`.
  - T0: Enable exec (and optionally browser): set `INSPECT_ENABLE_EXEC=1` (and `INSPECT_ENABLE_WEB_BROWSER=1` if needed). Always pair with approvals.

- Host (H):
  - H0: `sandbox="local"` (minimal isolation; dev only).
  - H1: `sandbox="docker"` (or `("docker", "compose.yaml")` for multi-service).
  - H2: `sandbox="k8s"` (use the Helm chart; remote, scalable; preferred for N1/N2).
  - H3: `sandbox="proxmox"` (remote VM isolation).

- Network (N):
  - H2/K8s: use chart values
    - N2: default (no internet) unless explicitly allowed
    - N1: `allowDomains: ["pypi.org", "files.pythonhosted.org", ...]`
    - N0: `allowDomains: "*"`
  - H1/Docker: default is general egress (N0). For N1/N2 use network policies, egress proxies, or compose-level network controls. Prefer K8s for fine-grained N1/N2.
  - H0/local: inherits host networking — avoid for untrusted tasks.

## Approvals (required for sensitive tools)

Attach approval policies to each Task via `approval=...`:
- `approval_preset("ci")`: permissive (iteration)
- `approval_preset("dev")`: escalate/reject sensitive tools by default
- `approval_preset("prod")`: terminate sensitive tools by default

Sensitive tools include `bash`, `python`, file-writes, and browser actions. Use stricter presets for demonstrations or in shared environments.

## Configuration snippets

- T2.H1.N2 (text-only, containerized, offline)
```python
from inspect_ai import Task
from inspect_ai.solver import generate

Task(
  solver=[generate()],
  sandbox="docker",
)
```

- T1.H1.N1 (web-only, allow-listed)
```bash
export INSPECT_ENABLE_WEB_SEARCH=1
# Docker: manage egress via proxy/firewall (recommend K8s for allow-listing)
```
```python
Task(
  solver=basic_agent(tools=[web_search()]),
  sandbox="docker",
)
```

- T0.H2.N1 (exec + restricted egress on K8s)
```bash
export INSPECT_ENABLE_EXEC=1
# in helm values: allowDomains: ["pypi.org", "files.pythonhosted.org"]
```
```python
Task(
  solver=basic_agent(tools=[bash(), python(), read_file(), write_file()]),
  sandbox="k8s",
  approval=approval_preset("dev"),
)
```

- T0.H3.N2 (exec in remote VM, no external net)
```python
Task(
  solver=basic_agent(tools=[bash(), python(), read_file(), write_file()]),
  sandbox="proxmox",
  approval=approval_preset("prod"),
)
```

## Defaults in this repository

- Example task (`examples/research/iterative_task.py`) sets `sandbox="local"` and attaches approvals; exec tools are enabled only when `-T enable_exec=true` is passed.
- A detailed integration guide for `inspect_agents` sandboxing is in `docs/how-to/sandboxing_inspect_agents.md`.

## Operational guidance

- Always log the selected `Tx.Hx.Nx` profile and all granted affordances.
- Prefer H2/H3 for untrusted or adversarial tasks; use H1 for portability; avoid H0 except in trusted local dev.
- Prefer N1/N2 for most research; justify N0 access and pair with approvals + audit trails.
- Keep CI runs in file-store mode (`INSPECT_AGENTS_FS_MODE=store`); only use `sandbox` FS mode when you need host interaction and preflight is healthy.
- Set explicit timeouts (`INSPECT_AGENTS_TOOL_TIMEOUT`) and keep output size limits default (Inspect enforces exec output caps; file tools have size ceilings).
- Redact secrets in logs/approvals; avoid exposing credentials to the model.

## Reference

- Full guidance PDF: `docs/reference/Technical_Guidance_on_SandBoxing.pdf`
- Inspect sandbox docs: Task `sandbox` parameter, providers (docker/k8s/proxmox), approvals, and tooling.

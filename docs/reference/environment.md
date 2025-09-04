# Environment Flags Reference

Centralized reference for environment variables that control providers/models,
tools, filesystem/sandbox, quarantine limits, logging, caching, and CI/test
behavior in this repo. Each section lists defaults, when-to-use guidance, and
example exports. See env_templates/inspect.env for a ready-to-copy template.

Links: guides on tools and safety
- Tool umbrellas and guidance: ../guides/tool-umbrellas.md
- Stateless vs stateful: ../guides/stateless-vs-stateful-tools-harmonized.md
- Sub-agent quarantine: ../guides/subagents.md
- Filesystem sandbox guardrails: ../adr/0004-filesystem-sandbox-guardrails.md
- Model roles + precedence: ../adr/0002-model-roles-map.md


## How Configuration Loads (Precedence)

- Real environment variables (highest precedence)
- Repository .env (if present)
- File pointed at by `INSPECT_ENV_FILE`
- Example template: env_templates/inspect.env (lowest precedence)

Tip
- Point the runner to a file: `--env-file env_templates/inspect.env`
- Or export: `export INSPECT_ENV_FILE=env_templates/inspect.env`


## Providers & Models (Role Mapping, Precedence)

- `DEEPAGENTS_MODEL_PROVIDER` (default: `ollama`)
  - Selects the provider when no explicit model prefix is given.
  - Examples: `ollama`, `lm-studio`, `openai`, `anthropic`, `google`, `groq`,
    `mistral`, `perplexity`, `fireworks`, `grok`, `goodfire`, `openrouter`.

- Role mapping (set per role; role name uppercased, hyphens→underscores)
  - `INSPECT_ROLE_<ROLE>_MODEL` — full path (`openai/gpt-4o-mini`) or bare
    tag (`llama3.1`).
  - `INSPECT_ROLE_<ROLE>_PROVIDER` — only needed if model is a bare tag.

- Global override (optional)
  - `INSPECT_EVAL_MODEL` — full Inspect model string (e.g., `openai/gpt-4o-mini`).
    If set to `none/none`, the override is ignored.

- Provider-specific keys and tags
  - Local providers
    - `OLLAMA_MODEL_NAME` (e.g., `llama3.1:8b`), optional `OLLAMA_BASE_URL`.
    - `LM_STUDIO_BASE_URL`, `LM_STUDIO_MODEL_NAME` (default `local-model`),
      `LM_STUDIO_API_KEY` (placeholder token OK for local).
  - Remote providers (require API keys + model tag)
    - `OPENAI_API_KEY`, `OPENAI_MODEL`
    - `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`
    - `GOOGLE_API_KEY`, `GOOGLE_MODEL`
    - `GROQ_API_KEY`, `GROQ_MODEL`
    - `MISTRAL_API_KEY`, `MISTRAL_MODEL`
    - `PERPLEXITY_API_KEY`, `PERPLEXITY_MODEL`
    - `FIREWORKS_API_KEY`, `FIREWORKS_MODEL`
    - `GROK_API_KEY`, `GROK_MODEL`
    - `GOODFIRE_API_KEY`, `GOODFIRE_MODEL`
    - `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`
  - OpenAI‑compatible vendors via `openai-api/<vendor>` also use
    `<VENDOR>_API_KEY` and `<VENDOR>_MODEL` (e.g., `LM_STUDIO_*`).

Resolution order (highest wins)
1) Explicit `model` with provider prefix (contains `/`).
2) Role mapping via `INSPECT_ROLE_<ROLE>_*`; otherwise use `inspect/<role>`.
3) `INSPECT_EVAL_MODEL` (when set to a concrete model, not `none/none`).
4) Provider: function arg → `DEEPAGENTS_MODEL_PROVIDER` → `ollama`.
5) Provider‑specific defaults/validation.

Examples
```bash
# Force OpenAI across the board
export DEEPAGENTS_MODEL_PROVIDER=openai
export OPENAI_API_KEY=... 
export OPENAI_MODEL=gpt-4o-mini

# Role mapping: grader uses a specific OpenAI model; others keep defaults
export INSPECT_ROLE_GRADER_PROVIDER=openai
export INSPECT_ROLE_GRADER_MODEL=gpt-4o-mini

# Local defaults
export OLLAMA_MODEL_NAME=llama3.1:8b
export LM_STUDIO_BASE_URL=http://127.0.0.1:1234/v1
export LM_STUDIO_MODEL_NAME=local-model
export LM_STUDIO_API_KEY=lm-studio
```


## Tool Toggles (When to Use)

- `INSPECT_ENABLE_THINK` (default: on when unset) — lightweight; safe to enable.
- `INSPECT_ENABLE_WEB_SEARCH` (default: off unless a provider is configured)
  - External providers
    - `TAVILY_API_KEY` (recommended for simplicity)
    - `GOOGLE_CSE_API_KEY` + `GOOGLE_CSE_ID`
  - Internal provider preference: `INSPECT_WEB_SEARCH_INTERNAL`
    (`openai|anthropic|perplexity|gemini|grok`) — optional augment.
- `INSPECT_ENABLE_EXEC` (bash, python) — keep off unless running in a sandbox
  with approvals.
- `INSPECT_ENABLE_WEB_BROWSER` — heavy; enable only with sandbox + approvals.
- `INSPECT_ENABLE_TEXT_EDITOR_TOOL` — optional; the file tools call the editor
  internally in sandbox mode, so exposing it directly is rarely needed.

Examples
```bash
# Enable light helpers
export INSPECT_ENABLE_THINK=1
export INSPECT_ENABLE_WEB_SEARCH=1
export TAVILY_API_KEY=...

# Power tools (only in sandboxed/dev environments)
export INSPECT_ENABLE_EXEC=1
export INSPECT_ENABLE_WEB_BROWSER=1
export INSPECT_ENABLE_TEXT_EDITOR_TOOL=1
```

See: ../guides/tool-umbrellas.md and ../getting-started/inspect_agents_quickstart.md


## Parallel Tool Execution (Kill‑Switch)

- `INSPECT_DISABLE_TOOL_PARALLEL` — truthy values (`1/true/yes/on`) force
  serial approval for non‑handoff tools within a single assistant turn. When the
  model emits multiple `tool_calls` and no handoff is present, only the first
  non‑handoff tool is approved; subsequent non‑handoff calls are rejected. A
  standardized transcript ToolEvent is emitted with
  `metadata.source="policy/parallel_kill_switch"` for skipped calls.
  Effective only when approval policies are active (the `dev`/`prod` presets
  include this policy; `ci` does not). Handoff tools remain serial and are
  governed by the handoff‑exclusivity policy.
- `INSPECT_TOOL_PARALLELISM_DISABLE` — legacy alias; supported for backward
  compatibility, but prefer `INSPECT_DISABLE_TOOL_PARALLEL`.

Examples
```bash
export INSPECT_DISABLE_TOOL_PARALLEL=1   # allow only the first non‑handoff tool per turn
```


## Filesystem & Sandbox (Mode, Safety, Limits)

- `INSPECT_AGENTS_FS_MODE` — `store` (default) | `sandbox`
  - `store`: in‑memory virtual FS (isolated per run).
  - `sandbox`: routes file ops through Inspect’s sandbox tools
    (`text_editor`; `bash_session` for `ls`).
- `INSPECT_AGENTS_TOOL_TIMEOUT` — per‑call tool timeout in seconds (default 15).
- `INSPECT_AGENTS_TYPED_RESULTS` — `1/true` to return typed objects from tools
  instead of strings/lists (default off).
- `INSPECT_SANDBOX_PREFLIGHT` — `auto` (default) | `skip` | `force`
  - `auto`: perform preflight; on failure, log a one‑time `files:sandbox_preflight` warning and fall back to store.
  - `skip`: return `False` from the preflight without logging; callers fall back deterministically.
  - `force`: perform preflight and raise on failure (no fallback). Intended for operator workflows where sandbox is mandatory.
- `INSPECT_SANDBOX_PREFLIGHT_TTL_SEC` — cache TTL in seconds for the preflight result (default `300`). Set `0` to disable caching and recheck each call.
- `INSPECT_SANDBOX_LOG_PATHS` — `1/true` to enrich the `files:sandbox_preflight` warning with contextual fields like `fs_root` and `tool`.
- `INSPECT_AGENTS_FS_READ_ONLY` — `1/true` enables audited read‑only mode in
  sandbox. When `INSPECT_AGENTS_FS_MODE=sandbox` and this flag is truthy,
  write/edit/delete operations are blocked: the files tool raises a
  `ToolException("SandboxReadOnly")` and emits a `tool_event` with
  `phase="error"` and `error="SandboxReadOnly"`. Listing and reading remain
  allowed. Has no effect in `store` mode.

See also
- Design discussion and pending decisions: ../design/open-questions.md#filesystem-sandbox-%E2%80%94-read-only-mode-new

Safety notes
- In sandbox mode, delete is intentionally disabled in the file tool to avoid
  removing host files.
- Paths are not validated for traversal; rely on sandbox isolation for
  untrusted input.

Examples
```bash
export INSPECT_AGENTS_FS_MODE=sandbox
export INSPECT_SANDBOX_PREFLIGHT=auto
export INSPECT_SANDBOX_PREFLIGHT_TTL_SEC=300
export INSPECT_SANDBOX_LOG_PATHS=1
export INSPECT_AGENTS_FS_READ_ONLY=1   # block write/edit/delete; allow ls/read
export INSPECT_AGENTS_TOOL_TIMEOUT=20
export INSPECT_AGENTS_TYPED_RESULTS=1
```

See: ../adr/0004-filesystem-sandbox-guardrails.md and ../guides/tool-umbrellas.md


## Quarantine & Limits (Sub‑Agent Handoffs)

- `INSPECT_QUARANTINE_MODE` — `strict` (default) | `scoped` | `off`
  - `strict`: remove tools/system; keep only boundary message.
  - `scoped`: strict + append small JSON summary of Todos/Files.
  - `off`: identity (debug only).
- `INSPECT_QUARANTINE_INHERIT` — `1/true` to cascade the parent filter to
  nested handoffs (default on).
- Per‑agent override: `INSPECT_QUARANTINE_MODE__<agent_name>` (normalized to
  lowercase; non‑alphanumeric→`_`; collapsed underscores).
- Scoped caps (when `mode=scoped`)
  - `INSPECT_SCOPED_MAX_BYTES` (default 2048)
  - `INSPECT_SCOPED_MAX_TODOS` (default 10)
  - `INSPECT_SCOPED_MAX_FILES` (default 20)

Examples
```bash
export INSPECT_QUARANTINE_MODE=strict
export INSPECT_QUARANTINE_INHERIT=1
export INSPECT_QUARANTINE_MODE__researcher=scoped
export INSPECT_SCOPED_MAX_BYTES=2048
```

See: ../guides/subagents.md


## Logging & Display

- `INSPECT_LOG_DIR` — transcript directory (default `.inspect/logs`).
- `INSPECT_TOOL_OBS_TRUNCATE` — max chars for string fields in tool logs before
  truncation (default 200).
- `INSPECT_TRACE_FILE` — optional tracing file path (recognized by Inspect
  runtime; useful during reviews).

Examples
```bash
export INSPECT_LOG_DIR=.inspect/logs
export INSPECT_TOOL_OBS_TRUNCATE=200
export INSPECT_TRACE_FILE=logs/inspect_ai/trace.log
```


## Cache & Retries

- `UV_CACHE_DIR` — cache directory for `uv` package installs (build speed).
- Retries: no repo‑specific knobs; provider SDKs may define their own.

Examples
```bash
export UV_CACHE_DIR=.uv-cache
```


## Test / CI Knobs

- `CI=1` — enable CI mode in tools/tests where honored.
- `NO_NETWORK=1` — default offline tests; ensure deterministic behavior.
- Useful pytest envs (optional):
  - `PYTEST_ADDOPTS="--maxfail=1 -q"`
  - `PYTHONWARNINGS=default`
  - `PYTHONHASHSEED=0`

Examples
```bash
export CI=1
export NO_NETWORK=1
export PYTEST_ADDOPTS="--maxfail=1 -q"
```


## Environment Files & Templates

- Point runners to a file with `--env-file` or `INSPECT_ENV_FILE`.
- Start from env_templates/inspect.env and customize as needed.

Examples
```bash
uv run python examples/inspect/run.py --env-file env_templates/inspect.env "..."
export INSPECT_ENV_FILE=env_templates/inspect.env
```

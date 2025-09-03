---
title: "Open Questions"
status: draft
owner: docs
updated: 2025-09-03
---

# Open Questions (Docs + Defaults)

This note captures unresolved decisions discovered while updating built‑in tool docs’ “Timeouts & Limits”. It links each question to concrete code and doc locations so we can decide and implement consistently.

## 1) Align non‑file tool timeouts (TBDs) — adopt 15s or tailor per‑tool?

- Context: File‑oriented built‑ins now document a 15s execution timeout driven by `INSPECT_AGENTS_TOOL_TIMEOUT` with a code default of 15.0s. 〖F:src/inspect_agents/tools_files.py†L105-L110〗 Also, `read_file` defaults to `limit=2000` lines and enforces per‑line truncation at 2000 chars. 〖F:src/inspect_agents/tools_files.py†L173-L180〗 〖F:src/inspect_agents/tools_files.py†L318-L326〗 The same 15s env‑backed default exists in the broader tools module, which our wrappers use. 〖F:src/inspect_agents/tools.py†L27-L44〗 〖F:src/inspect_agents/tools.py†L46-L48〗
- Gap: Several standard (non‑file) tool docs still show “TBD” timeouts:
  - bash: “Execution timeout: TBD. Output truncation caps: TBD.” 〖F:docs/tools/bash.md†L24-L26〗
  - python: “Execution timeout: TBD. Output truncation caps: TBD.” 〖F:docs/tools/python.md†L24-L26〗
  - think: “Execution timeout: TBD. Max length: TBD.” 〖F:docs/tools/think.md†L23-L24〗
  - text_editor: “Execution timeout: TBD. File size caps: TBD.” 〖F:docs/tools/text_editor.md†L24-L26〗
  - web_search: “Execution timeout: TBD. Provider quotas and API timeouts apply.” 〖F:docs/tools/web_search.md†L24-L25〗
  - web_browser_*: “Navigation/interaction timeouts: TBD. …” 〖F:docs/tools/web_browser.md†L25-L26〗

- Decision options:
  - A. Document a unified default: “Execution timeout: 15s (INSPECT_AGENTS_TOOL_TIMEOUT)” for all of the above, with notes where provider/tool may impose stricter caps (e.g., web_search providers, browser navs).
  - B. Tailor per‑tool: audit each tool’s actual behavior (e.g., parameterized `timeout`, provider defaults) and set distinct values/wording by tool.
  - C. Hybrid: set the unified 15s default, and explicitly call out exceptions where code/provider overrides exist or the tool exposes its own `timeout` arg.

- Recommendation: Start with Hybrid (C) for clarity and minimal drift. For `bash`/`python`, state default 15s and mention the optional `timeout` parameter; for `web_search`/`web_browser_*`, call out provider/session‑level behavior and quotas alongside the 15s agent‑side guard.

- Acceptance criteria:
  - All six docs above replace “TBD” with either the unified 15s default or tool‑specific text, with a one‑line rationale when provider/tool overrides apply.
  - Any tool exposing a `timeout` parameter states precedence vs. the global default.

## 2) Centralize defaults to avoid drift — shared “Tool Defaults” doc?

- Context: Several defaults are now normative in code:
  - Global timeout: `INSPECT_AGENTS_TOOL_TIMEOUT` → 15s default. 〖F:src/inspect_agents/tools_files.py†L105-L110〗
  - Files/read defaults: `limit=2000` lines and per‑line truncation 2000 chars. 〖F:src/inspect_agents/tools_files.py†L173-L180〗 〖F:src/inspect_agents/tools_files.py†L318-L326〗 Also mirrored by strict input models. 〖F:src/inspect_agents/tool_types.py†L22-L23〗
  - Observability truncation for tool args/logs: `INSPECT_TOOL_OBS_TRUNCATE` → 200 chars default. 〖F:src/inspect_agents/tools.py†L46-L48〗
  - Typed results toggle: `INSPECT_AGENTS_TYPED_RESULTS` (truthy strings) controls typed vs. string output. 〖F:src/inspect_agents/tools_files.py†L113-L118〗

- Problem: Repeating these facts across many tool docs risks inconsistencies.

- Proposal: Add a single reference page (e.g., `docs/tools/_defaults.md` or a “Global Defaults” section under `docs/guides/tool-umbrellas.md`) that enumerates:
  - Core env vars and defaults (timeout, FS mode, typed results, obs truncation).
  - File‑tool specific read/write/edit behaviors and caps.
  - Guidance on provider‑imposed limits (web search/browser) and how they interact with the global timeout.

- Recommendation: Create `docs/tools/_defaults.md` and link it from each tool’s “Timeouts & Limits”. This keeps tool pages concise and reduces maintenance load.

- Acceptance criteria:
  - New shared page with the above values and code‑backed citations.
  - Each tool doc references the shared page in “Source of Truth” or “Timeouts & Limits”.

---

Next actions if approved:
- Update the six non‑file tool docs to replace “TBD” using the Hybrid approach (Q1).
- Author `docs/tools/_defaults.md` with the centralized values and cross‑links (Q2).

## 3) Surface unified `files` tool beyond tools index

- Context: We added a unified `files` reference and linked it from the tools index alongside wrapper tools; it is not yet highlighted in top‑level docs/guides. 〖F:docs/tools/README.md†L12-L21〗
- Options:
  - Add a brief call‑out + link in `docs/README.md` and relevant guides (tool umbrellas; stateless vs stateful) that positions `files` as the primary file interface.
  - Keep visibility limited to the tools index to avoid duplication.
- Decision: Where to surface `files` beyond the tools index; owner: docs; target: next docs sweep.

## 4) Guide‑level call‑out: `delete_file` is store‑only (sandbox disabled)

- Context: Code disables delete in sandbox and the wrapper advertises store‑only; reference pages document this but guides don’t. 〖F:src/inspect_agents/tools_files.py†L586-L620〗 〖F:src/inspect_agents/tools_files.py†L647-L651〗 〖F:src/inspect_agents/tools.py†L656-L661〗
- Options:
  - Add a “Danger”/“Security” callout in the tools umbrella guide explaining sandbox vs store behaviors with explicit delete caveat.
  - Add a short “FS modes” subsection to the stateless‑vs‑stateful guide reiterating delete constraints.
  - Leave as reference‑only to reduce guide noise.
- Decision: Whether/where to add the call‑out; owner: docs; target: next guides edit.

## 5) Promote `files` and `delete_file` docs from draft → stable

- Context: Both pages are marked `status: draft` in front matter. 〖F:docs/tools/files.md†L1-L7〗 〖F:docs/tools/delete_file.md†L1-L7〗
- Proposed criteria:
  - Run a docs link check/site build to verify anchors/cross‑links.
  - Confirm parameter names and result shapes against validation/executors (typed results flag; timeout). 〖F:src/inspect_agents/tools_files.py†L666-L684〗
  - Confirm delete remains disabled in sandbox for the upcoming release.
- Decision: When to flip status; owner: docs; target: this or next release.

---

## 3) Typed Results Docs — Examples and Placement

- Context: File tools support typed results when `INSPECT_AGENTS_TYPED_RESULTS` is truthy; otherwise they return legacy strings/lists. We need to decide where and how to show example outputs for both modes.
- Evidence:
  - Env gating parsed in `_use_typed_results()` (truthy values: 1/true/yes/on). 〖F:src/inspect_agents/tools_files.py†L113-L118〗
  - `read_file` typed `lines[]` are cat‑style numbered strings; formatting/truncation in `_format_lines(...)`. 〖F:src/inspect_agents/tools_files.py†L318-L326〗
  - Sandbox vs store summaries differ for `read_file` (sandbox appends “(sandbox mode)”; store includes a concrete line range). 〖F:src/inspect_agents/tools_files.py†L359-L369〗 〖F:src/inspect_agents/tools_files.py†L421-L429〗
  - Per‑tool pages already list typed schemas in Result Schema bullets (e.g., ls/write/edit/delete). 〖F:docs/tools/ls.md†L19-L22〗 〖F:docs/tools/write_file.md†L20-L23〗 〖F:docs/tools/edit_file.md†L23-L26〗 〖F:docs/tools/delete_file.md†L20-L23〗
- Open question: Should we embed explicit typed vs legacy examples on every tool page, or centralize examples in one doc and link out?
- Options:
  - A) Per‑page examples (typed JSON + legacy string) for every tool.
  - B) Centralized “Typed vs Legacy” guide with canonical examples; per‑tool pages link out.
  - C) Hybrid: full examples on `read_file`; minimal one‑liners elsewhere; plus a consolidated table in `docs/tools/README.md`.
- Proposed: Hybrid (C). Default to typed examples; include a one‑line callout showing how to switch to legacy.

## 4) Summary Wording Stability — Exact Strings vs Invariants

- Context: Some docs quote tool summary strings verbatim. Exact phrases can change, creating doc drift.
- Evidence:
  - `read_file` sandbox path summary includes “(sandbox mode)”; store path summary includes an explicit line range. 〖F:src/inspect_agents/tools_files.py†L359-L369〗 〖F:src/inspect_agents/tools_files.py†L421-L429〗
- Open question: Do we document exact strings or describe invariants and show non‑normative examples?
- Options:
  - A) Quote exact strings for each backend path (precise but brittle).
  - B) Describe invariants (count/path/backend/range) and show illustrative examples (resilient; lower maintenance).
- Proposed: B) Document invariants with examples labeled “example output”; avoid treating phrasing as stable API.

---

## FS Clarifications — Follow‑ups (2025‑09‑03)

These questions arose while clarifying sandbox vs store behavior across file tools and docs. Each item includes context, evidence, and a proposed direction.

### Q1. Include sandbox‑delete notice in the `files` ToolDef description?

- Context: The `files_tool()` docstring already calls out that delete is disabled in sandbox. The `ToolDef.description` is concise and omits this nuance.
- Evidence: Docstring explicitly says “Delete is disabled in sandbox mode” 〖F:src/inspect_agents/tools_files.py†L647-L651〗, while the ToolDef description is only “Unified file operations tool (ls, read, write, edit, delete).” 〖F:src/inspect_agents/tools_files.py†L721-L722〗.
- Options:
  - A) Keep description short; rely on per‑command docs and the docstring.
  - B) Append a short clause: “Delete disabled in sandbox mode”.
  - C) Add a “Sandbox vs Store” callout in tools index and link out from the description via docs.
- Recommendation: B) Append a 5–7 word clause for high‑signal safety without bloating the description.

### Q2. Make `read` caps configurable via env (line cap, default limit)?

- Context: `read` truncates each line at 2000 chars and defaults to `limit=2000` lines. These are hardcoded constants today.
- Evidence: Default `limit=2000` in params 〖F:src/inspect_agents/tools_files.py†L176-L180〗 and per‑line truncation in formatter 〖F:src/inspect_agents/tools_files.py†L323-L324〗.
- Options:
  - A) Leave as constants (docs already state the caps).
  - B) Introduce env flags (e.g., `INSPECT_READ_MAX_LINE_CHARS`, `INSPECT_READ_DEFAULT_LIMIT`) and document in Environment Reference.
  - C) Allow per‑call overrides only (new optional params) and keep defaults constant.
- Recommendation: C) Prefer explicit per‑call params (backward‑compatible with defaults). Consider B later if a global is needed in CI.

### Q3. Propagate sandbox/store wording to any remaining tool pages?

- Context: We updated how‑to, `files`, and `ls` pages. Individual wrapper pages (`read_file`, `write_file`, `edit_file`, `delete_file`) already contain sandbox/store notes, but consistency could be improved.
- Evidence: How‑to routing and notes updated (store‑mode `ls` lists in‑memory Files) 〖F:docs/how-to/filesystem.md†L37-L41〗; `files` page now states store‑mode `ls` reads from in‑memory Files 〖F:docs/tools/files.md†L48-L54〗; `ls` docs describe sandbox proxy via `bash_session('ls -1')` 〖F:docs/tools/ls.md†L26-L28〗.
- Open item: Audit non‑FS docs index (`docs/tools/README.md`) for a one‑line FS note, and verify each FS wrapper’s “Sandbox Notes” section uses consistent phrasing.
- Proposal: Add a checklist to the docs backlog to review `read_file`, `write_file`, `edit_file` wordings for the next sweep.

### Q4. Echo the exact sandbox‑delete error string across tool docs?

- Context: Code raises a specific message to guide users to switch to store mode. `delete_file` docs now reflect it verbatim; other pages mention a generic ToolException.
- Evidence: Error string in code 〖F:src/inspect_agents/tools_files.py†L617-L620〗; `delete_file` page updated to match 〖F:docs/tools/delete_file.md†L27-L29〗; `files` page still generic 〖F:docs/tools/files.md†L48-L53〗.
- Options:
  - A) Quote the exact message everywhere (higher coupling).
  - B) Keep generic on non‑delete pages; link to `delete_file` for details.
  - C) Describe invariant + provide one canonical example (on `delete_file` only).
- Recommendation: B) Keep generic on other pages; centralize the exact message on `delete_file` and how‑to.

### Q5. Add a one‑liner in Tools index: “ls (store) lists in‑memory Files store”?

- Context: Tools index has a general sandbox note but not the store‑mode `ls` nuance; new users may assume host FS.
- Evidence: Tools index present 〖F:docs/tools/README.md†L1-L21〗; store‑mode `ls` clarification exists in how‑to 〖F:docs/how-to/filesystem.md†L37-L40〗.
- Options:
  - A) Add a short bullet under “Built‑in (Inspect Agents)” or a “Notes” block.
  - B) Rely on per‑tool pages only.
- Recommendation: A) Add a succinct one‑liner with a link to the how‑to page.

---

## Appendix — Docs & UX Items (Detailed Context)

### Delete File Docs — Store‑Only vs. Hidden Until Sandbox Support

- Context: The `delete_file` wrapper delegates to the unified `files` tool with `command='delete'`. Current behavior supports deletion only in store‑backed mode; sandbox mode intentionally blocks host‑file deletes for safety. This limitation is currently more visible in code than in docs.
- Options:
  - A) Document now with a prominent “Not supported in sandbox” callout on both `files` and `delete_file` pages, including an example of the error payload and a short rationale (sandbox guardrails).
  - B) Hide from public tool lists until sandbox semantics land; keep minimal API reference only.
  - C) Place under an “Advanced / Store‑only” section and exclude from quickstarts.
- Decision drivers: clarity and transparency vs. surface‑area confusion; security posture; parity with other FS operations.
- Proposed default: A — document now with a clear banner and example; link to the filesystem sandbox ADR; add a test that asserts the sandbox error shape.
- Next steps: add “Sandbox: not supported” banners, error example, and rationale to `docs/tools/files.md` and the wrapper page; ensure the quickstart index does not suggest sandbox deletes.

### Env Reference — Add `INSPECT_MODEL_DEBUG` (Model Resolution Trace)

- Context: The model‑roles ADR recommends a debug flag to print a non‑secret resolution trace (role → source → final model) to aid troubleshooting of role maps and provider defaults.
- Options:
  - A) Add `INSPECT_MODEL_DEBUG=0|1` to the environment reference now, marked as “proposed; will print a non‑secret trace when resolving models”.
  - B) Wait until the implementation lands to avoid drift.
- Decision drivers: immediate troubleshooting value vs. documenting an unimplemented switch.
- Proposed default: A — document with a clear “proposed” label and update once merged; include a short, redacted snippet illustrating the output.
- Next steps: wire the flag in the resolver to emit a structured, secret‑safe trace; add a doc snippet and a unit test that asserts redaction behavior.

### Provider Troubleshooting Defaults — Ollama Tag and Port

- Context: This repo defaults to Ollama for local runs and uses a small qwen tag as the out‑of‑the‑box model. Many failures stem from mis‑set tags or base URL/port mismatches.
- Options:
  - A) Recommend a known‑good small tag (qwen) and document the default base URL `http://localhost:11434`, plus a quick validation step (`curl $OLLAMA_BASE_URL/api/tags` or `ollama list`).
  - B) Prefer llama3.x small tags to match examples in several docs.
  - C) Present both qwen and llama small tags with guidance on when to choose which (CPU‑only vs. VRAM), and keep the default port guidance.
- Proposed default: C — present both families, keep the default port guidance, and add a short “Verify your local provider” checklist to Getting Started and the Environment Reference.
- Next steps: update `docs/getting-started/*` and `docs/reference/environment.md` with tag/port guidance and a validation snippet.

### Retries & Cache — Guide vs. Reference; “Proposed” Label

- Context: The “Retries & Cache” guide lists an env surface marked as “proposed” until the knobs land in code.
- Options:
  - A) Keep the detailed how‑to in the Guide and add a slim Reference table of env keys (clearly labeled “proposed”) in the Environment Reference.
  - B) Move everything to Reference and drop the Guide framing.
  - C) Keep both, but generate the Reference table from code once implemented to avoid drift.
- Proposed default: A → Guide remains primary; add a small env table in Reference with a “proposed” banner and remove the banner once code is merged.
- Next steps: add the Reference table; ensure examples/runner accept overrides via env with `__<AGENT_NAME>` suffixes.

### FS Tooling Docs IA — Unified Page vs. Per‑Tool Pages

- Context: We need to choose the primary information architecture for filesystem tools documentation.
- Options:
  - A) Single canonical page for the unified `files` tool (subcommands: ls/read/write/edit/delete) that also documents shared semantics (truncation, offsets, uniqueness, error codes), with thin wrapper pages (`read_file`, `write_file`, etc.) linking back.
  - B) Keep full per‑tool pages and factor out a shared “Filesystem Semantics” section all pages reference.
  - C) Hybrid: canonical `files` page plus thin per‑tool pages that host concise examples and a “Config Keys” block; both link to a shared semantics anchor.
- Proposed default: C — prevents duplication while keeping discoverability for common verbs; minimizes drift by centralizing tricky semantics.
- Next steps: draft `docs/tools/files.md` as canonical; convert wrapper pages to thin stubs with examples and cross‑links.

## Sandbox FS Preflight & Fallback — Decision Drivers & Env Flags

- Context: Filesystem tool calls may route to Inspect’s sandbox (text editor, bash session). A one‑time preflight determines availability and governs fallbacks; behavior is configurable. This section surfaces the open decisions and their drivers.

- Preflight mode toggle:
  - auto (default): preflight once; on failure, log a one‑time warning and fall back to Store FS.
  - skip: never attempt sandbox; go straight to Store FS; log that preflight was skipped by config.
  - force: require sandbox; if unavailable, raise `PrerequisiteError` with guidance. 〖F:docs/backlog/rewrite/NOTE-sandbox-preflight.md†L17-L21〗

- Cache scope & refresh:
  - Sticky (process‑wide) cache: zero hot‑path overhead; may become stale if sandbox appears mid‑run.
  - TTL cache: recheck every N seconds (e.g., 300s) and log once if availability flips.
  - Explicit reset: expose `reset_sandbox_preflight()` for long‑lived services/tests. 〖F:docs/backlog/rewrite/NOTE-sandbox-preflight.md†L24-L27〗

- Warning context details:
  - Minimal default fields in the warning event (tool, phase, ok, reason, fs_mode) plus upstream text; paths are potentially sensitive.
  - Opt‑in path context via `INSPECT_SANDBOX_LOG_PATHS=1` to include cwd basename or VCS‑relative path. 〖F:docs/backlog/rewrite/NOTE-sandbox-preflight.md†L30-L33〗

- Proposed environment variables:
  - `INSPECT_SANDBOX_PREFLIGHT=auto|skip|force` (default: auto)
  - `INSPECT_SANDBOX_LOG_PATHS=0|1` (default: 0)
  - `INSPECT_SANDBOX_PREFLIGHT_TTL=<seconds>` (optional; default unset → sticky cache). 〖F:docs/backlog/rewrite/NOTE-sandbox-preflight.md†L41-L44〗

- Recommended direction (for docs and implementation notes):
  - Keep default `auto` with sticky cache for simplicity and zero hot‑path overhead.
  - Provide explicit `force` (strict prod) and `skip` (constrained CI) modes.
  - Offer `reset` helper; defer TTL unless a concrete use case emerges.
  - Keep warnings minimal by default; gate path context behind an env flag. 〖F:docs/backlog/rewrite/NOTE-sandbox-preflight.md†L35-L39〗

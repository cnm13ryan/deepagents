# done — TODO — Model Resolver (Inspect-native)

Context & Motivation
- Replace LangChain model selection with Inspect model/role resolution driven by env vars and parameters.

Implementation Guidance
- Read: `src/deepagents/model.py` for current env-based selection  
  Grep: `get_default_model`, `DEEPAGENTS_MODEL_PROVIDER`, `OLLAMA_MODEL_NAME`
- Inspect model calls occur inside agent loops via `get_model().generate(...)`

- Scope — Do
- [ ] Add `src/inspect_agents/model.py` with:
  - [ ] `def resolve_model(provider: str|None=None, model: str|None=None, role: str|None=None) -> str` returning either an explicit model name or an Inspect role string (e.g., `"inspect/<role>"`) to pass directly to `react(model=...)`.
- [ ] Tests in `tests/inspect_agents/test_model.py` for env precedence and defaults

Scope — Don’t
- No LangChain imports; do not modify Inspect submodule

Success Criteria
- [ ] Agents configured with resolver run without errors
- [ ] Unit tests cover env overrides and defaults

Recommended Defaults
- Prefer local (Ollama) models when available; otherwise require explicit env configuration (e.g., `OPENAI_API_KEY` + `OPENAI_MODEL`) and fail fast with a clear error and guidance.
 - Prefer passing role strings to `react(model=...)` for sub-agents; the resolver remains a thin mapping from roles/env → provider-specific names.

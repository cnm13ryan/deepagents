# Testing Guide — Model Resolution

Validate provider/model resolution behavior and role handling.

## What to verify
- Provider + bare model yields `provider/model` (e.g., `ollama/llama3.1`).
- Fully-qualified models pass through unchanged (e.g., `openai/gpt-4o-mini`).

## Patterns
- Use provided example runners under `examples/research/` in subprocesses to avoid importing heavy stacks in-process.
- Build env with local `PYTHONPATH`, set `NO_NETWORK=1` and `CI=1` for determinism.

## Examples
- Direct resolver usage (faster than subprocess):
  ```python
  from inspect_agents.model import resolve_model

  def test_provider_model_combination():
      assert resolve_model(provider="ollama", model="llama3.1").startswith("ollama/")

  def test_passthrough_fully_qualified():
      assert resolve_model(model="openai/gpt-4o-mini") == "openai/gpt-4o-mini"
  ```

- Diagnostics without scraping logs:
  ```python
  from inspect_agents.model import resolve_model_explain

  def test_explain_paths_and_inputs(monkeypatch):
      monkeypatch.delenv("INSPECT_EVAL_MODEL", raising=False)
      monkeypatch.setenv("DEEPAGENTS_MODEL_PROVIDER", "lm-studio")
      monkeypatch.setenv("LM_STUDIO_MODEL_NAME", "local-model")
      model, info = resolve_model_explain()
      assert model == "openai-api/lm-studio/local-model"
      assert info["path"] == "provider_lm_studio"
      assert info["provider_arg"] is None  # came from env
  ```

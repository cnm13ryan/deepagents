

from inspect_agents.model import resolve_model_explain


def _clear_common_env(monkeypatch):
    for var in [
        "DEEPAGENTS_MODEL_PROVIDER",
        "INSPECT_EVAL_MODEL",
        "OLLAMA_MODEL_NAME",
        "LM_STUDIO_MODEL_NAME",
        "INSPECT_ROLE_RESEARCHER_MODEL",
        "INSPECT_ROLE_RESEARCHER_PROVIDER",
        "INSPECT_ROLE_CODER_MODEL",
        "INSPECT_ROLE_CODER_PROVIDER",
    ]:
        monkeypatch.delenv(var, raising=False)


def test_explain_explicit_model_with_provider(monkeypatch):
    _clear_common_env(monkeypatch)

    model, info = resolve_model_explain(model="openai/gpt-4o-mini")
    assert model == "openai/gpt-4o-mini"
    assert info["path"] == "explicit_model_with_provider"
    assert info["model_arg"] == "openai/gpt-4o-mini"
    assert info["provider_arg"] is None
    assert info["final"] == model


def test_explain_role_indirection_no_mapping(monkeypatch):
    _clear_common_env(monkeypatch)

    model, info = resolve_model_explain(role="researcher")
    assert model == "inspect/researcher"
    assert info["path"] == "role_inspect_indirection"
    assert info["role_env_model"] is None
    assert info["role_env_provider"] is None


def test_explain_role_env_mapping_provider_in_model(monkeypatch):
    _clear_common_env(monkeypatch)
    monkeypatch.setenv("INSPECT_ROLE_CODER_MODEL", "ollama/llama3.1")

    model, info = resolve_model_explain(role="coder")
    assert model == "ollama/llama3.1"
    assert info["path"] == "role_env_mapping"
    assert info["role_env_provider"] == "ollama"
    assert info["role_env_model"] == "llama3.1"


def test_explain_env_INSPECT_EVAL_MODEL(monkeypatch):
    _clear_common_env(monkeypatch)
    monkeypatch.setenv("INSPECT_EVAL_MODEL", "openai-api/lm-studio/qwen3")

    model, info = resolve_model_explain()
    assert model == "openai-api/lm-studio/qwen3"
    assert info["path"] == "env_INSPECT_EVAL_MODEL"
    assert info["env_inspect_eval_model"] == "openai-api/lm-studio/qwen3"


def test_explain_provider_lm_studio(monkeypatch):
    _clear_common_env(monkeypatch)
    monkeypatch.setenv("DEEPAGENTS_MODEL_PROVIDER", "lm-studio")
    monkeypatch.setenv("LM_STUDIO_MODEL_NAME", "qwen/qwen3-4b-thinking-2507")

    model, info = resolve_model_explain()
    assert model == "openai-api/lm-studio/qwen/qwen3-4b-thinking-2507"
    assert info["path"] == "provider_lm_studio"
    assert info["provider_arg"] is None


def test_explain_provider_ollama_default(monkeypatch):
    _clear_common_env(monkeypatch)
    monkeypatch.setenv("OLLAMA_MODEL_NAME", "llama3.1")

    model, info = resolve_model_explain()
    assert model == "ollama/llama3.1"
    assert info["path"] == "provider_ollama"
    assert info["env_inspect_eval_model"] is None


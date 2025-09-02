import os
import pytest

from inspect_agents.model import resolve_model


def test_default_prefers_ollama(monkeypatch):
    # Clear env that could influence default
    for var in [
        "DEEPAGENTS_MODEL_PROVIDER",
        "INSPECT_EVAL_MODEL",
        "OLLAMA_MODEL_NAME",
    ]:
        monkeypatch.delenv(var, raising=False)

    result = resolve_model()
    assert result.startswith("ollama/")
    # Should include the default tag when OLLAMA_MODEL_NAME not set
    assert "qwen3:4b-thinking-2507-q4_K_M" in result


def test_lm_studio_env_override(monkeypatch):
    monkeypatch.setenv("DEEPAGENTS_MODEL_PROVIDER", "lm-studio")
    monkeypatch.setenv("LM_STUDIO_MODEL_NAME", "qwen/qwen3-4b-thinking-2507")

    result = resolve_model()
    assert result == "openai-api/lm-studio/qwen/qwen3-4b-thinking-2507"


def test_role_passthrough(monkeypatch):
    # If role is provided and no explicit model, return inspect/<role>
    monkeypatch.delenv("INSPECT_EVAL_MODEL", raising=False)
    result = resolve_model(role="grader")
    assert result == "inspect/grader"


def test_openai_requires_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError) as e:
        resolve_model(provider="openai", model="gpt-4o-mini")
    assert "OPENAI_API_KEY" in str(e.value)


def test_explicit_model_with_prefix_returned_as_is(monkeypatch):
    result = resolve_model(model="ollama/llama3.1")
    assert result == "ollama/llama3.1"


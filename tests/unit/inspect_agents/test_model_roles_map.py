import pytest

from inspect_agents.model import resolve_model


def test_role_env_mapping_ollama(monkeypatch):
    monkeypatch.setenv("INSPECT_ROLE_RESEARCHER_MODEL", "ollama/llama3.1")
    # Clear conflicting globals
    monkeypatch.delenv("INSPECT_EVAL_MODEL", raising=False)
    monkeypatch.delenv("DEEPAGENTS_MODEL_PROVIDER", raising=False)

    result = resolve_model(role="researcher")
    assert result == "ollama/llama3.1"


def test_role_env_mapping_openai_requires_key(monkeypatch):
    monkeypatch.setenv("INSPECT_ROLE_RESEARCHER_MODEL", "openai/gpt-4o-mini")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError) as e:
        resolve_model(role="researcher")
    assert "OPENAI_API_KEY" in str(e.value)


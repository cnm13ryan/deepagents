import pytest

from inspect_agents.model import resolve_model


def test_openai_api_vendor_requires_api_key(monkeypatch):
    """Vendor path under openai-api/<vendor> requires <VENDOR>_API_KEY."""
    # Ensure no vendor key is present
    monkeypatch.delenv("LM_STUDIO_API_KEY", raising=False)
    with pytest.raises(RuntimeError) as e:
        resolve_model(provider="openai-api/lm-studio", model="local-model")
    assert "LM_STUDIO_API_KEY" in str(e.value)


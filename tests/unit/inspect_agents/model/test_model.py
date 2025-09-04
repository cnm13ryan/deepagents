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
    # Ensure global overrides don't leak in from other tests (e.g., integration
    # test sets INSPECT_EVAL_MODEL via os.environ.setdefault)
    monkeypatch.delenv("INSPECT_EVAL_MODEL", raising=False)
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


def test_model_debug_logging_when_flag_set(monkeypatch, caplog):
    """Test that debug logging occurs when INSPECT_MODEL_DEBUG is set."""
    monkeypatch.setenv("INSPECT_MODEL_DEBUG", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")  # Mock API key to avoid RuntimeError
    monkeypatch.delenv("DEEPAGENTS_MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("INSPECT_EVAL_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL_NAME", raising=False)

    with caplog.at_level("INFO"):
        result = resolve_model(provider="openai", model="gpt-4")

    assert result == "openai/gpt-4"

    # Should have exactly one log record from model resolution
    model_logs = [record for record in caplog.records if "Model resolution:" in record.getMessage()]
    assert len(model_logs) == 1

    log_message = model_logs[0].getMessage()
    assert "role=None" in log_message
    assert "provider_arg=openai" in log_message
    assert "model_arg=gpt-4" in log_message
    assert "final=openai/gpt-4" in log_message
    assert "path=provider_openai" in log_message


def test_model_debug_logging_when_flag_not_set(monkeypatch, caplog):
    """Test that no debug logging occurs when INSPECT_MODEL_DEBUG is not set."""
    monkeypatch.delenv("INSPECT_MODEL_DEBUG", raising=False)
    monkeypatch.delenv("DEEPAGENTS_MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("INSPECT_EVAL_MODEL", raising=False)

    with caplog.at_level("INFO"):
        result = resolve_model()

    assert result.startswith("ollama/")

    # Should have no debug log records
    model_logs = [record for record in caplog.records if "Model resolution:" in record.getMessage()]
    assert len(model_logs) == 0


def test_role_mapping_debug_logging_when_flag_set(monkeypatch, caplog):
    """Test that role mapping debug logging occurs when INSPECT_MODEL_DEBUG is set."""
    monkeypatch.setenv("INSPECT_MODEL_DEBUG", "1")
    monkeypatch.setenv("INSPECT_ROLE_RESEARCHER_MODEL", "custom-model")  # Bare model without provider

    with caplog.at_level("INFO"):
        result = resolve_model(role="researcher")

    assert result == "ollama/custom-model"

    # Should have both role mapping and model resolution log records
    role_logs = [record for record in caplog.records if "Role mapping resolution:" in record.getMessage()]
    model_logs = [record for record in caplog.records if "Model resolution:" in record.getMessage()]

    assert len(role_logs) == 1
    assert len(model_logs) == 1

    role_log_message = role_logs[0].getMessage()
    assert "role=researcher" in role_log_message
    assert "path=bare_model_tag" in role_log_message

    model_log_message = model_logs[0].getMessage()
    assert "path=provider_ollama" in model_log_message


def test_role_mapping_with_provider_debug_logging(monkeypatch, caplog):
    """Test role mapping debug logging with provider in model string."""
    monkeypatch.setenv("INSPECT_MODEL_DEBUG", "1")
    monkeypatch.setenv("INSPECT_ROLE_RESEARCHER_MODEL", "ollama/custom-model")

    with caplog.at_level("INFO"):
        result = resolve_model(role="researcher")

    assert result == "ollama/custom-model"

    # Should have both role mapping and model resolution log records
    role_logs = [record for record in caplog.records if "Role mapping resolution:" in record.getMessage()]
    model_logs = [record for record in caplog.records if "Model resolution:" in record.getMessage()]

    assert len(role_logs) == 1
    assert len(model_logs) == 1

    role_log_message = role_logs[0].getMessage()
    assert "role=researcher" in role_log_message
    assert "path=provider_in_model" in role_log_message

    model_log_message = model_logs[0].getMessage()
    assert "path=provider_ollama" in model_log_message


def test_explicit_model_with_provider_debug_path(monkeypatch, caplog):
    """Test debug path for explicit model with provider prefix."""
    monkeypatch.setenv("INSPECT_MODEL_DEBUG", "1")

    with caplog.at_level("INFO"):
        result = resolve_model(model="anthropic/claude-3-sonnet")

    assert result == "anthropic/claude-3-sonnet"

    model_logs = [record for record in caplog.records if "Model resolution:" in record.getMessage()]
    assert len(model_logs) == 1

    log_message = model_logs[0].getMessage()
    assert "path=explicit_model_with_provider" in log_message
    assert "final=anthropic/claude-3-sonnet" in log_message


def test_inspect_role_indirection_debug_path(monkeypatch, caplog):
    """Test debug path for Inspect role indirection."""
    monkeypatch.setenv("INSPECT_MODEL_DEBUG", "1")
    monkeypatch.delenv("INSPECT_ROLE_CODER_MODEL", raising=False)
    monkeypatch.delenv("INSPECT_ROLE_CODER_PROVIDER", raising=False)

    with caplog.at_level("INFO"):
        result = resolve_model(role="coder")

    assert result == "inspect/coder"

    role_logs = [record for record in caplog.records if "Role mapping resolution:" in record.getMessage()]
    model_logs = [record for record in caplog.records if "Model resolution:" in record.getMessage()]

    assert len(role_logs) == 1
    assert len(model_logs) == 1

    role_log_message = role_logs[0].getMessage()
    assert "path=no_model_env" in role_log_message

    model_log_message = model_logs[0].getMessage()
    assert "path=role_inspect_indirection" in model_log_message


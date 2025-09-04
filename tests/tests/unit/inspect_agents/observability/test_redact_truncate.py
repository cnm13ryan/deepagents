# test(obs): ensure nested redaction and truncation behavior

from inspect_agents.observability import _redact_and_truncate


def test_redact_and_truncate_nested_payload():
    payload = {
        "api_key": "SECRET",
        "content": "x" * 500,  # top-level 'content' should be redacted
        "description": "y" * 500,  # top-level non-sensitive long string should be truncated
        "args": {
            "content": "x" * 500,  # nested long string is not truncated by helper
            "token": "tok",
            "authorization": "Bearer abc",
            "ok": True,
        },
    }
    out = _redact_and_truncate(payload, max_len=100)

    # Top-level redaction
    assert out["api_key"] != "SECRET"

    # Top-level 'content' is redacted, not truncated
    assert out["content"] == "[REDACTED]"

    # Truncation suffix present for top-level non-sensitive long string fields
    assert isinstance(out["description"], str)
    assert out["description"].endswith("chars]")

    # Nested long strings remain unmodified by this helper
    assert not out["args"]["content"].endswith("chars]")

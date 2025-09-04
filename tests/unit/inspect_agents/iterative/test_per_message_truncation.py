import types

from inspect_agents._conversation import (
    prune_messages,  # noqa: F401 (import ensures module loads)
    truncate_conversation_tokens,
    truncate_message_tokens,
)


class FakeTokenizer:
    def encode(self, text: str, disallowed_special=()):  # noqa: ARG002
        # Char-level tokenization for deterministic tests
        return [ord(c) for c in text]

    def decode(self, ids):
        return "".join(chr(i) for i in ids)


def _msg(role: str, content):
    # Minimal message-like object compatible with our helpers
    return types.SimpleNamespace(role=role, content=content)


def test_truncate_message_tokens_string_basic():
    tok = FakeTokenizer()
    m = _msg("user", "A" * 1000)

    out = truncate_message_tokens(m, max_tokens=100, tokenizer=tok)
    assert out is m  # mutated in place is acceptable
    assert "tokens trimmed" in out.content
    # Ensure we kept both head and tail segments
    assert out.content.startswith("A" * 10)
    assert out.content.endswith("A" * 10)


def test_truncate_message_tokens_list_content_proportional():
    tok = FakeTokenizer()
    # Two text-bearing chunks and one non-text chunk
    chunks = [
        {"type": "text", "text": "X" * 300},
        {"type": "reasoning", "reasoning": "Y" * 700},
        {"type": "image", "image_url": {"url": "http://example"}},
    ]
    m = _msg("assistant", chunks)

    out = truncate_message_tokens(m, max_tokens=200, tokenizer=tok)
    # Ensure non-text chunk preserved
    assert any(c.get("type") == "image" for c in out.content)
    text = next(c for c in out.content if c.get("type") == "text")["text"]
    reasoning = next(c for c in out.content if c.get("type") == "reasoning")["reasoning"]
    assert "tokens trimmed" in text or "tokens trimmed" in reasoning
    # Total kept across text chunks should not exceed cap significantly
    kept = sum(len(s) for s in (text, reasoning))
    assert kept <= 220  # allow small overhead for marker text


def test_truncate_conversation_tokens_last_k_scope():
    tok = FakeTokenizer()
    msgs = [
        _msg("system", "sys"),
        _msg("user", "U" * 300),
        _msg("assistant", "A" * 300),
        _msg("tool", "T" * 300),
        _msg("assistant", "B" * 600),  # only this one should be truncated with last_k=1
    ]

    out = truncate_conversation_tokens(msgs, max_tokens_per_msg=100, last_k=1, tokenizer=tok)

    # First assistant remains unchanged
    assert out[2].content == "A" * 300
    # Tool untouched
    assert out[3].content == "T" * 300
    # Last assistant truncated
    assert "tokens trimmed" in out[4].content


def test_tool_and_system_messages_untouched():
    tok = FakeTokenizer()
    msgs = [
        _msg("system", "S" * 1000),
        _msg("tool", "Z" * 1000),
    ]
    out = truncate_conversation_tokens(msgs, max_tokens_per_msg=10, last_k=10, tokenizer=tok)
    assert out[0].content == "S" * 1000
    assert out[1].content == "Z" * 1000


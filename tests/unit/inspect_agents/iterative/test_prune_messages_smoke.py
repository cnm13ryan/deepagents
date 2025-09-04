import types

from inspect_agents._conversation import prune_messages


def _msg(role: str, content=None, **kw):
    return types.SimpleNamespace(role=role, content=content, **kw)


def test_prune_messages_smoke():
    sys_msg = _msg("system", "S")
    u1 = _msg("user", "U1")
    a1 = _msg("assistant", "", tool_calls=[types.SimpleNamespace(id="1", function="ls", arguments={})])
    t1 = _msg("tool", "ok", tool_call_id="1")
    junk = _msg(
        "assistant",
        "Context too long; please summarize recent steps and continue.",
    )
    msgs = [sys_msg, u1, a1, t1, junk] + [_msg("user", f"U{i}") for i in range(2, 8)]

    pruned = prune_messages(msgs, keep_last=4)
    assert pruned[0].role == "system"
    assert pruned[1].role == "user"
    # Overflow hint removed
    assert all(m is not junk for m in pruned)
    # Tool kept only when paired with its assistant
    assert any(getattr(m, "tool_call_id", None) == "1" for m in pruned)


import random

import pytest

from inspect_agents._conversation import prune_messages

pytestmark = pytest.mark.benchmark


def _synthetic_messages(n_users: int = 50, n_assist: int = 50):
    msgs = []
    # Always keep a system + first user
    msgs.append(type("M", (), {"role": "system"})())
    msgs.append(type("M", (), {"role": "user", "content": "U1"})())
    # Interleave assistant/user chatter; no tool pairing for speed
    for i in range(max(n_users, n_assist)):
        if i < n_assist:
            msgs.append(type("M", (), {"role": "assistant", "content": f"A{i}"})())
        if i < n_users:
            msgs.append(type("M", (), {"role": "user", "content": f"U{i+2}"})())
    # Add synthetic overflow hints sparsely
    for _ in range(5):
        idx = random.randint(2, len(msgs) - 1)
        msgs.insert(idx, type("M", (), {"role": "assistant", "content": "Context too long; please summarize recent steps and continue."})())
    return msgs


def test_prune_messages_perf(benchmark):
    msgs = _synthetic_messages(200, 200)
    benchmark(lambda: prune_messages(msgs, keep_last=40))


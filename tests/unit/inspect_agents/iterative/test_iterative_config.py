
import pytest

from inspect_agents.iterative_config import (
    resolve_pruning,
    resolve_time_and_step_limits,
    resolve_truncation,
)


def test_time_and_steps_args_precede_env(monkeypatch):
    monkeypatch.setenv("INSPECT_ITERATIVE_TIME_LIMIT", "1")
    monkeypatch.setenv("INSPECT_ITERATIVE_MAX_STEPS", "2")

    t, s = resolve_time_and_step_limits(real_time_limit_sec=9, max_steps=8)
    assert t == 9 and s == 8


@pytest.mark.parametrize(
    "env_val,expected",
    [("5", 5), ("0", None), ("-3", None), ("", None), (None, None), ("xyz", None)],
)
def test_time_limit_env_fallback(monkeypatch, env_val, expected):
    monkeypatch.delenv("INSPECT_ITERATIVE_TIME_LIMIT", raising=False)
    if env_val is None:
        pass
    else:
        monkeypatch.setenv("INSPECT_ITERATIVE_TIME_LIMIT", env_val)

    t, _ = resolve_time_and_step_limits(real_time_limit_sec=None, max_steps=None)
    assert t == expected


@pytest.mark.parametrize(
    "env_val,expected",
    [("5", 5), ("0", None), ("-3", None), ("", None), (None, None), ("xyz", None)],
)
def test_step_limit_env_fallback(monkeypatch, env_val, expected):
    monkeypatch.delenv("INSPECT_ITERATIVE_MAX_STEPS", raising=False)
    if env_val is None:
        pass
    else:
        monkeypatch.setenv("INSPECT_ITERATIVE_MAX_STEPS", env_val)

    _, s = resolve_time_and_step_limits(real_time_limit_sec=None, max_steps=None)
    assert s == expected


def test_pruning_after_env_applies_only_on_none_or_default(monkeypatch):
    # Env should apply when arg is None
    monkeypatch.setenv("INSPECT_PRUNE_AFTER_MESSAGES", "100")
    after, keep = resolve_pruning(prune_after_messages=None, prune_keep_last=40)
    assert after == 100 and keep == 40

    # Env should NOT override explicit non-default arg
    monkeypatch.setenv("INSPECT_PRUNE_AFTER_MESSAGES", "200")
    after2, _ = resolve_pruning(prune_after_messages=90, prune_keep_last=40)
    assert after2 == 90

    # Non-positive disables (None)
    monkeypatch.setenv("INSPECT_PRUNE_AFTER_MESSAGES", "0")
    after3, _ = resolve_pruning(prune_after_messages=None, prune_keep_last=40)
    assert after3 is None


def test_pruning_keep_last_env_only_when_default(monkeypatch):
    # Default keep=40 -> env applies
    monkeypatch.setenv("INSPECT_PRUNE_KEEP_LAST", "30")
    _, keep = resolve_pruning(prune_after_messages=None, prune_keep_last=40)
    assert keep == 30

    # Non-default keep -> env ignored
    monkeypatch.setenv("INSPECT_PRUNE_KEEP_LAST", "25")
    _, keep2 = resolve_pruning(prune_after_messages=None, prune_keep_last=12)
    assert keep2 == 12

    # Negative clamps to 0
    monkeypatch.setenv("INSPECT_PRUNE_KEEP_LAST", "-7")
    _, keep3 = resolve_pruning(prune_after_messages=None, prune_keep_last=40)
    assert keep3 == 0


def test_truncation_cap_env_when_arg_none(monkeypatch):
    # Env positive -> applies
    monkeypatch.setenv("INSPECT_PER_MSG_TOKEN_CAP", "50")
    cap, last_k = resolve_truncation(per_msg_token_cap=None, truncate_last_k=200)
    assert cap == 50 and last_k == 200

    # Env empty -> None
    monkeypatch.setenv("INSPECT_PER_MSG_TOKEN_CAP", "")
    cap2, _ = resolve_truncation(per_msg_token_cap=None, truncate_last_k=200)
    assert cap2 is None

    # Arg provided -> env ignored
    monkeypatch.setenv("INSPECT_PER_MSG_TOKEN_CAP", "100")
    cap3, _ = resolve_truncation(per_msg_token_cap=10, truncate_last_k=200)
    assert cap3 == 10


def test_truncation_last_k_env_overrides(monkeypatch):
    # Env overrides any arg when set and > 0
    monkeypatch.setenv("INSPECT_TRUNCATE_LAST_K", "2")
    cap, last_k = resolve_truncation(per_msg_token_cap=None, truncate_last_k=200)
    assert last_k == 2

    # Invalid/zero -> keep arg
    monkeypatch.setenv("INSPECT_TRUNCATE_LAST_K", "0")
    _, last_k2 = resolve_truncation(per_msg_token_cap=None, truncate_last_k=123)
    assert last_k2 == 123


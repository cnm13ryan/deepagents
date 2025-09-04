# test(run): ensure run_agent propagates/raises limit errors correctly

import sys
import types

import pytest


@pytest.mark.asyncio
async def test_run_agent_returns_state_only_without_limits(monkeypatch):
    """Engine returns a plain state when no limits are provided."""
    # Stub engine to return a plain state object
    engine_mod = types.ModuleType("inspect_ai.agent._run")

    class State:  # simple sentinel type
        pass

    async def fake_run(agent, input, limits=None):
        # run_agent forwards the default [] when no limits are supplied
        assert limits == []
        return State()

    engine_mod.run = fake_run
    monkeypatch.setitem(sys.modules, "inspect_ai.agent._run", engine_mod)

    from inspect_agents.run import run_agent

    out = await run_agent(agent=object(), input="start")
    assert isinstance(out, State)


@pytest.mark.asyncio
async def test_run_agent_tuple_return_and_raise_on_limit(monkeypatch):
    """When engine returns (state, err), support tuple return and raising."""
    engine_mod = types.ModuleType("inspect_ai.agent._run")

    class State:
        pass

    class LimitExceededError(RuntimeError):
        pass

    async def fake_run(agent, input, limits=None):
        return State(), LimitExceededError("boom")

    engine_mod.run = fake_run
    monkeypatch.setitem(sys.modules, "inspect_ai.agent._run", engine_mod)

    from inspect_agents.run import run_agent

    # Return (state, err) when flagged
    state, err = await run_agent(agent=object(), input="x", return_limit_error=True)
    assert isinstance(state, State)
    assert isinstance(err, RuntimeError)

    # Raise when flagged
    with pytest.raises(RuntimeError):
        await run_agent(agent=object(), input="x", raise_on_limit=True)

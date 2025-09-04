# Testing Guide — Mocking (pytest-mock)

Use `pytest-mock` for clean, scoped mocking and spying.

## Patterns
- Patch attributes: `mocker.patch('pkg.mod.attr', new=...)` or `mocker.patch.object(obj, 'name', ...)`.
- Spies: `spy = mocker.spy(obj, 'method')`; assert `spy.call_count`, `spy.call_args`.
- Autospeccing: prefer to patch concrete functions/attrs rather than whole modules where possible.

## Scope & Cleanup
- Mocks are automatically undone after each test; avoid manual teardown.
- For heavy module stubs (e.g., `inspect_ai.approval._apply`), install module objects in `sys.modules` inside the test and remove them after if they’re not test-scoped (see approval tests for patterns).

## Examples
- Spy and patch example:
  ```python
  def test_log_tool_event_spy(mocker):
      import inspect_agents.tools as tools
      spy = mocker.spy(tools, "_log_tool_event")
      tools._log_tool_event(name="x", phase="start")
      assert spy.call_count == 1

  def test_patch_env_flag(mocker):
      import os
      mocker.patch.dict(os.environ, {"INSPECT_AGENTS_TYPED_RESULTS": "1"}, clear=False)
      from inspect_agents.tools import _use_typed_results
      assert _use_typed_results() is True
  ```

## References
- pytest-mock usage.

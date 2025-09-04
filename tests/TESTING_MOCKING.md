# Testing Guide — Mocking (pytest-mock)

Use `pytest-mock` for clean, scoped mocking and spying.

## Patterns
- Patch attributes: `mocker.patch('pkg.mod.attr', new=...)` or `mocker.patch.object(obj, 'name', ...)`.
- Spies: `spy = mocker.spy(obj, 'method')`; assert `spy.call_count`, `spy.call_args`.
- Autospeccing: prefer to patch concrete functions/attrs rather than whole modules where possible.

## Scope & Cleanup
- Mocks are automatically undone after each test; avoid manual teardown.
- For heavy module stubs (e.g., `inspect_ai.approval._apply`), install module objects in `sys.modules` inside the test and remove them after if they’re not test-scoped. See patterns in approval tests. 〖F:tests/integration/inspect_agents/test_approval.py†L57-L66〗

## References
- pytest-mock usage.

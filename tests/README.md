# Test Structure

The tests have been organized into three main categories:

## Fixtures (`tests/fixtures/`)
Test helpers, utilities, and shared components. Currently contains configuration files and shared test setup.

## Unit Tests (`tests/unit/`)
Individual component testing. These tests focus on testing single units of functionality in isolation:

- `test_model.py` - Model resolution and configuration
- `test_tool_schema.py` - Tool schema validation
- `test_config_loader.py` - Configuration loading functionality
- `test_logging.py` - Logging system testing
- `test_migration.py` - Migration logic testing
- `test_state.py` - State management testing
- `test_tool_error_codes.py` - Error code handling
- `test_fs_tools.py` - Individual file system tools
- `test_fs_sandbox.py` - File system sandbox functionality
- `test_todos_tool.py` - Todo tool functionality

## Integration Tests (`tests/integration/`)
Multi-component interaction testing. These tests verify that different components work correctly together:

- `test_subagents.py` - Subagent system interactions
- `test_approval_chains.py` - Approval chain workflow testing
- `test_run.py` - Full execution workflow testing
- `test_tool_timeouts.py` - Tool timeout handling across components
- `test_truncation.py` - Content truncation in workflows
- `test_parallel.py` - Parallel execution testing
- `test_supervisor.py` - Supervisor functionality testing
- `test_approval.py` - Approval system integration

## Running Tests

Run all tests:
```bash
CI=1 NO_NETWORK=1 uv run pytest
```

Run tests by category:
```bash
# Unit tests only
CI=1 NO_NETWORK=1 uv run pytest tests/unit/

# Integration tests only
CI=1 NO_NETWORK=1 uv run pytest tests/integration/

# Fixtures (if any test files are added)
CI=1 NO_NETWORK=1 uv run pytest tests/fixtures/
```

Run a specific test file:
```bash
CI=1 NO_NETWORK=1 uv run pytest tests/unit/inspect_agents/test_model.py
```

## Test Collection

Verify test collection without running:
```bash
CI=1 NO_NETWORK=1 uv run pytest --collect-only -q tests/
```
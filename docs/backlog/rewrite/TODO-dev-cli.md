# DONE — Dev CLI

Context & Motivation
- Provide a simple command-line entry to run the Inspect-based supervisor for demos, local testing, and quick validation.

Implementation Guidance
- Add a small CLI module (e.g., `src/inspect_agents/cli.py`) with `main()` that:
  - Parses prompt/model/limits/approval profile flags
  - Builds supervisor (and sub-agents if config provided)
  - Calls `init_tool_approval(...)` and `agent.run(...)`
- Optionally expose as a console script in `pyproject.toml`

Scope — Do
- [x] Implement CLI with minimal deps; support flags to enable standard tools
- [x] Document usage in README/examples; ensure it runs

Scope — Don’t
- Don’t bundle provider keys or assume network connectivity by default

Success Criteria
- [x] `uv run python examples/inspect/run.py --help` works
- [x] Running with a sample prompt produces transcript and expected results

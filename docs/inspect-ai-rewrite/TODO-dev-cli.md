# TODO — Dev CLI

Context & Motivation
- Provide a simple command-line entry to run the Inspect-based supervisor for demos, local testing, and quick validation.

Implementation Guidance
- Add a small CLI module (e.g., `src/inspect_agents/cli.py`) with `main()` that:
  - Parses prompt/model/limits/approval profile flags
  - Builds supervisor (and sub-agents if config provided)
  - Calls `init_tool_approval(...)` and `agent.run(...)`
- Optionally expose as a console script in `pyproject.toml`

Scope — Do
- [ ] Implement CLI with minimal deps; support `--config` (YAML) and `--log-dir`
- [ ] Document usage in README; ensure it runs examples

Scope — Don’t
- Don’t bundle provider keys or assume network connectivity by default

Success Criteria
- [ ] `python -m inspect_agents.cli --help` works
- [ ] Running with a sample config produces transcript and expected results

# Contributing to deepagents

We welcome contributions of all kinds — bug fixes, docs, tests, and new examples. This guide helps you get set up quickly and submit high‑quality changes.

## Getting Started

- Requirements: Python 3.11+ (we test on 3.12), macOS/Linux.
- Clone and create a virtual environment:
  ```bash
  python3.11 -m venv .venv && source .venv/bin/activate
  pip install -e '.[dev,testing,utilities]'
  ```
- Local Inspect‑AI source path (for tests/examples that use the bundled checkout):
  ```bash
  export PYTHONPATH=src:external/inspect_ai/src
  ```

## Development Workflow

- Lint & Format (Ruff):
  ```bash
  ruff check .
  ruff format .
  ```
- Run unit tests:
  ```bash
  CI=1 NO_NETWORK=1 PYTHONPATH=src:external/inspect_ai/src pytest -q tests/unit/inspect_agents
  ```
- Optional coverage:
  ```bash
  pytest --cov=src --cov-report=term-missing -q tests/unit/inspect_agents
  ```

## Commit Style

- Use Conventional Commits for clarity and changelogs, e.g.:
  - `feat(agents): add handoff limits`  
  - `fix(tools): correct sandbox editor fallback`  
  - `docs(readme): clarify install instructions`

## Pull Requests

- Link an issue when applicable and include a brief rationale.
- Keep PRs focused and reasonably small; large refactors should be discussed first.
- Include tests for new behavior and regressions. Prefer deterministic, offline tests (set `NO_NETWORK=1`).
- Ensure CI is green (lint + tests). GitHub Actions workflows live under `.github/workflows`.

## Reporting Issues

- Provide steps to reproduce, expected vs actual behavior, and logs if relevant.
- Include your Python version and platform (e.g., macOS 14, Ubuntu 22.04).
- If it’s a tooling issue, note any environment flags used (e.g., `INSPECT_ENABLE_*`).

## Code of Conduct

- This project adheres to a Code of Conduct. If `CODE_OF_CONDUCT.md` is not present yet, we follow the [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). Please be kind and respectful.

## Release Process (maintainers)

- Ensure version is bumped in `pyproject.toml` using semver.
- Tag the release (e.g., `v0.0.x`) and publish to PyPI if applicable.
- Update CHANGELOG and README badges if needed.

Thanks for contributing to deepagents!

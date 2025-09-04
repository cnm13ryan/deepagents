# Testing Guide — Coverage (pytest-cov / coverage.py)

## Defaults
- Coverage config is in `pyproject.toml`; sources `src/`, omits `*/tests/*`, and excludes common lines (repr, NotImplemented, etc.).

## Running
- Quick run with coverage summary: `uv run pytest -q --cov=src --cov-report=term`
- HTML report: add `--cov-report=html` and open `htmlcov/index.html`.

## Tips
- Focus on behavior, not line count; prefer meaningful assertions over chasing 100%.
- Exclude slow/external paths unless explicitly needed.

## References
- pytest-cov docs (options and reports).
- coverage.py configuration reference.

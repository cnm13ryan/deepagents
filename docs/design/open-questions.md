# Open Questions — Tests Layout and Harness

Context: Following the test suite reorganization on 2025-09-04, we centralized
pytest setup in `tests/conftest.py`, converted the manual truncation runner into
pytest, added `__init__.py` files to unit domain folders, standardized markers in
integration suites, and updated the tests README with domain run examples.

This document records remaining open decisions with enough detail to resolve them
asynchronously and track rationale.

## 1) Where should the integration offline-hardening fixture live?

- Current state
  - A suite-local bootstrap exists at `tests/integration/inspect_agents/conftest.py` that:
    - Ensures `src/` is on `sys.path` for direct imports; and
    - Applies an `@pytest.fixture(autouse=True)` that neutralizes environment leakage
      for integration tests (clears any global approvals; disables heavy/optional
      tools; unsets common web-search provider keys; and defaults to `NO_NETWORK=1`).
  - Root-level `tests/conftest.py` already handles path setup and global guide
    surfacing, plus optional dependency shims, but intentionally does not include
    the autouse offline-hardening fixture.

- Why it matters
  - Keeping the hardening fixture local to the `inspect_agents` integration package
    reduces blast radius for contributors running unrelated tests or different
    packages under `tests/integration/` in the future.
  - Moving the hardening into the root conftest would guarantee consistent defaults
    across all tests, but could surprise unit tests that rely on specific env
    toggles (e.g., enabling optional tools locally) unless they explicitly override.

- Options
  1) Keep hardening fixture scoped to `tests/integration/inspect_agents/` (status quo).
     - Pros: Minimal behavior change; isolation for integration-only; less risk of
       altering unit tests’ environment; alignment with “heavy operations only in
       integration” principle.
     - Cons: If additional integration packages are added later, they won’t inherit
       the hardening unless they copy or import the fixture; slight duplication risk.
  2) Lift hardening fixture into root `tests/conftest.py` and gate by marker or path.
     - Pros: Single source of truth; zero duplication for future suites; consistent
       offline defaults across the board.
     - Cons: Broadens impact to unit tests; requires careful scoping (e.g., apply
       only when a test node id starts with `tests/integration/` or when a marker
       is present); more conditional logic in the root conftest.
  3) Centralize in a helper module and import where needed.
     - Pros: DRY without forcing global behavior; easy reuse in new integration
       packages via `from tests.helpers.offline import harden_env`.
     - Cons: Slight indirection; still requires per-package import wiring.

- Recommendation (tentative)
  - Choose (1) for now: keep the fixture scoped to `tests/integration/inspect_agents/`.
    It matches current needs and avoids unintended side effects on unit tests.
  - If/when another integration area is added, refactor to (3) by extracting the
    hardening into `tests/helpers/offline.py` and importing it from each package
    `conftest.py`.

- Acceptance criteria to close
  - Document chosen scope in `tests/README.md`.
  - If (3) is chosen later: introduce `tests/helpers/offline.py`, update affected
    `conftest.py` files to import/use it, and remove duplicate logic.

- Related files
  - `tests/integration/inspect_agents/conftest.py` (fixture implementation)
  - `tests/conftest.py` (central setup and shims)

---

If additional questions emerge (e.g., expanding the marker taxonomy, introducing
strict network budgets for selected suites, or adopting a rule to always prefer
role-based markers over keyword heuristics), append them here with a similar
structure: current state → why it matters → options → recommendation → criteria.


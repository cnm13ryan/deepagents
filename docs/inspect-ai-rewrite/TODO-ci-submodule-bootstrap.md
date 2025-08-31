# TODO — CI & Submodule Bootstrap

Context & Motivation
- Ensure CI checks out submodules and runs tests for the new Inspect-native modules reliably.

Implementation Guidance
- Workflow file: `.github/workflows/ci.yml` (create/update)  
  Grep: `submodules:`, `git submodule update --init --recursive`

Scope — Do
- [ ] CI: checkout with `submodules: recursive`
- [ ] Python 3.11 matrix; install with `pip` or `uv`; cache wheels
- [ ] Run tests for this repo (not Inspect submodule)
- [ ] Document `git clone --recurse-submodules` in README

Scope — Don’t
- Don’t run Inspect’s own test suite

Success Criteria
- [ ] CI green on PRs for `inspect-ai-rewrite`
- [ ] Fresh clone with `--recurse-submodules` works per README


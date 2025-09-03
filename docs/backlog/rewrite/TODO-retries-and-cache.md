# TODO — Retries & Cache

Context & Motivation
- Improve robustness to transient model/provider issues and reduce latency/cost by caching repeat generations.

Implementation Guidance
- basic_agent supports `cache: bool | CachePolicy` passed to `get_model().generate(..., cache=cache)`
- Retry helpers: `external/inspect_ai/src/inspect_ai/model/_retry.py`

Scope — Do
- [ ] Add a configurable cache policy (env/arg) for supervisor/sub-agents
- [ ] Define retry policy (max attempts, backoff, jitter) for transient failures
- [ ] Tests simulate a transient failure and assert retry; test cached response reuse

Scope — Don’t
- Don’t enable cache by default for tests that assert specific token usage or message flow

Success Criteria
- [ ] Retries occur on configured exceptions; no infinite loops
- [ ] Cache reduces duplicate latency in a repeat scenario

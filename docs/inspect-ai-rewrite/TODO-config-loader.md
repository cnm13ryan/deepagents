# TODO — Config Loader (YAML)

Context & Motivation
- Allow declaring agents, tools, models, and approvals in YAML for easy iteration, environment variants, and CI profiles.

Implementation Guidance
- YAML parsing (safe_load); map to `react(...)`, `handoff(...)`, tool lists, policy presets
- Consider schema validation (pydantic models) to catch typos

Scope — Do
- [ ] Define YAML schema: supervisor prompt, subagent list (name, description, prompt, tools, model), approvals, limits
- [ ] Implement loader that returns a ready-to-run supervisor + sub-agent tool list
- [ ] Tests: minimal config loads and runs; invalid config yields clear validation errors

Scope — Don’t
- Don’t attempt to mirror Inspect’s internal registry; keep mapping explicit and simple

Success Criteria
- [ ] Example config spins up the supervisor with sub-agents and approvals; tests pass

# TODO — Model Roles Map

Context & Motivation
- Provide role-based model selection (e.g., researcher, coder, editor) with environment overrides for providers/models.

Implementation Guidance
- Pass roles to `react(model=...)` as strings or use provider-specific names
- Maintain a mapping `role -> provider/model` using env vars (e.g., `INSPECT_ROLE_RESEARCHER_MODEL`)
 - Coordinate with the Model Resolver so both paths stay consistent (roles → concrete model name)

Scope — Do
- [ ] Define default role set and mapping resolution order (env > repo defaults)
- [ ] Tests: sub-agent configured with a role receives the expected model

Scope — Don’t
- Don’t bake provider secrets into code; rely on env

Success Criteria
- [ ] Roles resolve deterministically; misconfigurations fail with actionable errors

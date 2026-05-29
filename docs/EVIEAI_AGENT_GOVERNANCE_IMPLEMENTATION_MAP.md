# EvieAI Agent Governance Gateway - Implementation Map

## Goal
Build an "agent-native governance gateway" capability inside EvieAI to provide:
- full observability and lineage for every agent action
- centralized policy enforcement for MCP/tool/model/API access
- enterprise-grade auditability without blocking adoption

## Desired Outcomes
- 100% of tool invocations attributable to user, agent, session, and resource
- policy decisions enforced in real time with p95 overhead under 50 ms
- complete audit reconstruction for any user/agent run
- safe rollout model (audit -> warn -> enforce)

## Target Architecture (Mapped to EvieAI)
- Orchestrator: policy decision point (PDP), trace orchestration, identity context propagation
- MCP servers: policy enforcement points (PEP) for tool-level constraints and telemetry events
- SQL/Dashboard stack: governance analytics, policy hit reporting, incident timelines
- Auth layer: identity-aligned attribution and scoped token brokering
- Web UI: governance console (inventory, approvals, violations, audit replay)

## Phased Delivery Plan

### Phase 0 - Discovery and Baseline (Week 1)
Objective:
- baseline current tool traffic, auth model, and observability gaps

Work:
- inventory all MCP endpoints and tool operations
- classify data sensitivity per tool/domain
- define governance event schema

Exit Criteria:
- signed-off baseline report
- approved governance event model

### Phase 1 - End-to-End Observability (Weeks 2-3)
Objective:
- capture lineage across user -> orchestrator -> model -> MCP/tool -> downstream API

Work:
- add global trace_id/request_id propagation
- emit structured governance events from orchestrator and MCP servers
- create initial agent inventory view and run timeline

Exit Criteria:
- every request has correlated trace chain
- inventory dashboard shows active agents, tools, and usage

### Phase 2 - Policy Engine MVP (Weeks 4-6)
Objective:
- enforce access controls at runtime with low latency

Work:
- implement policy middleware in orchestrator
- policies: allow/deny by role, agent, tool group, environment, time window
- support modes: audit, warn, enforce

Exit Criteria:
- policy decision applied on all tool calls
- deny/warn events visible in dashboard with reason codes

### Phase 3 - Enterprise MCP Catalog and Hardened Tool Variants (Weeks 7-8)
Objective:
- centralize approved tools and constrain high-risk operations

Work:
- build vetted tool registry (owner, risk score, status)
- create hardened variants with parameter constraints and row/token caps
- add pre-approval workflow for new tool onboarding

Exit Criteria:
- only approved tools discoverable in production
- hardened variants used for high-risk integrations

### Phase 4 - Identity-Aligned Access and Secretless Brokering (Weeks 9-10)
Objective:
- map every tool action to verified identity with least privilege

Work:
- propagate user identity claims through orchestrator path
- implement scoped short-lived credentials/tokens for downstream access
- remove static/shared credential use in runtime paths

Exit Criteria:
- per-action identity attribution is complete
- shared credential usage removed from interactive tool flows

### Phase 5 - Risk Evaluation Sandbox and Rollout Controls (Weeks 11-12)
Objective:
- prevent unsafe policies/tools from reaching production

Work:
- add trace replay sandbox for what-if policy simulations
- detect risky tool patterns and data exfiltration indicators
- enforce promotion gates (sandbox pass required)

Exit Criteria:
- all policy/tool changes validated in sandbox first
- production promotion controlled by explicit approval

### Phase 6 - Reliability and Cost Guardrails (Weeks 13-14)
Objective:
- avoid outages/cost spikes while scaling governed AI usage

Work:
- rate limits, retry budgets, and circuit breakers per tool/provider
- token/cost budgets per user/team/agent
- anomaly alerts for usage and spend spikes

Exit Criteria:
- measurable reduction in failed tool cascades
- budget alerts active and tested

### Phase 7 - Governance Console GA (Weeks 15-16)
Objective:
- operationalize governance for security, platform, and product teams

Work:
- UI for policy management, approvals, audit replay, and incident drill-down
- governance KPIs and SLA reporting
- runbooks for incident and exception handling

Exit Criteria:
- stakeholders can manage policies and audit flows without engineering support
- GA sign-off with operational readiness checklist complete

## Cross-Cutting Requirements
- Performance: policy and audit instrumentation overhead must stay within SLO
- Security: immutable audit logs, RBAC, and environment separation
- Compliance: retention policy and exportable audit evidence
- Developer UX: default-safe, low-friction onboarding for new tools

## GitHub Project Mapping
Create one Project with the following top-level epics:
1. Epic: Observability and Lineage
2. Epic: Policy Engine and Enforcement
3. Epic: MCP Catalog and Tool Hardening
4. Epic: Identity and Token Brokering
5. Epic: Risk Sandbox and Promotion Gates
6. Epic: Reliability and Cost Guardrails
7. Epic: Governance Console and Operations

Recommended status columns:
- Backlog
- Ready
- In Progress
- Blocked
- In Review
- Done

Recommended labels:
- governance
- security
- platform
- orchestrator
- mcp
- ui
- telemetry
- policy
- reliability
- cost

## Acceptance KPIs
- Attribution coverage >= 99.9%
- Policy evaluation latency p95 < 50 ms
- Audit replay completeness = 100% for sampled incidents
- High-risk tool calls blocked/approved according to policy with zero bypass
- Governance rollout completed without production regression

## Risks and Mitigations
- Overblocking disrupts teams:
  - Mitigation: staged rollout with warn mode and exception flow
- Context/token bloat from telemetry payloads:
  - Mitigation: summarize for chat paths, full fidelity for dashboard/audit paths
- Increased complexity in auth flows:
  - Mitigation: standardized token broker abstraction and integration tests

## Immediate Next 10 Execution Tasks
1. Finalize governance event schema and trace conventions
2. Add orchestrator middleware for request and policy context
3. Add MCP server telemetry wrappers for tool calls
4. Stand up initial governance tables and retention strategy
5. Implement policy engine MVP with audit mode
6. Build policy decision logging and reason taxonomy
7. Create approved tool catalog model and onboarding workflow
8. Add token/secret brokering abstraction in auth path
9. Build first governance dashboard (inventory + denies + timeline)
10. Enable staged rollout controls (audit/warn/enforce) per environment

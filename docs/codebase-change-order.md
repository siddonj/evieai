# EvieAI Codebase Change Order (Priority Sequence)

## Goal
Implement connector abstraction + bitemporal data foundation with minimal breakage, then layer in streaming, signals, and write-back controls.

---

## Phase 0 — Guardrails (Day 0)
1. Freeze schema-affecting feature work on legacy aigent2 branch.
2. Add architecture decision records (ADRs) for:
   - Connector interface contract
   - Bitemporal data model
   - Audit ledger immutability strategy
3. Add baseline integration smoke tests around existing ingestion paths.

**Exit criteria:** ADRs approved, baseline tests passing.

---

## Phase 1 — Connector Core (Week 1)
1. Introduce `connectors/` module into main codebase:
   - `base.py` (Connector Protocol)
   - `types.py` (Page, Event, WriteResult, HealthStatus)
   - `registry.py` (registration, capability filtering, health report)
2. Create adapter stubs:
   - `PropexoAdapter`
   - `WebhookAdapter`
3. Add config schema for connector registration (tenant-scoped).
4. Wire registry into app startup and health endpoint.

**Exit criteria:** app boots with registry; health endpoint shows registered connectors.

---

## Phase 2 — Bitemporal Persistence (Week 2)
1. Apply bitemporal migration foundation (`valid_*`, `recorded_*`, confidence, lineage).
2. Add `audit_ledger` append-only table + hash chaining.
3. Refactor ingestion writes:
   - close existing open system records (`superseded_at`)
   - insert new version row (never in-place mutate historical facts)
4. Add helper SQL/views:
   - `as_of_valid_time`
   - `as_of_system_time`
   - `current_snapshot`

**Exit criteria:** ingestion writes versioned rows; historical replay query works.

---

## Phase 3 — Event Ingress + Signal Plumbing (Week 3)
1. Add webhook ingress endpoint with signature verification.
2. Publish normalized events to event bus (NATS/Redpanda).
3. Add signal processor service to correlate events with canonical entities.
4. Persist generated signals as first-class entities with reason chains.

**Exit criteria:** webhook event in → signal entity out with traceable lineage.

---

## Phase 4 — Agent Tooling Integration (Week 4)
1. Expose connector/entity freshness tools in MCP:
   - `get_connector_freshness`
   - `get_entity_lineage`
   - `get_confidence_breakdown`
2. Expose bitemporal query tools:
   - `query_as_of(time)`
   - `diff_between(t1, t2)`
3. Update prompts/tool policy so LLM cites lineage and freshness.

**Exit criteria:** user-facing answers include source + freshness + confidence.

---

## Phase 5 — Safe Write-Back (Week 5)
1. Add `Actions` service for upstream writes.
2. Enforce:
   - idempotency keys
   - policy checks
   - approval queue (human-in-the-loop for high-risk writes)
   - circuit breakers per connector
3. Log every write intent/result to `audit_ledger`.

**Exit criteria:** one end-to-end controlled write-back flow in production (pilot tenant).

---

## Phase 6 — Evaluation + Reliability (Week 6)
1. Add eval harness (grounding, citation accuracy, hallucination rate).
2. Add connector contract tests and replay tests.
3. Add observability dashboards (sync lag, event lag, write failures, model spend).
4. Define SLOs:
   - ingestion freshness
   - workflow completion
   - action success rate

**Exit criteria:** release gate enforced by eval and reliability metrics.

---

## Suggested File Touch Order in Existing Codebase
1. `app startup / dependency injection`
2. `ingestion services`
3. `DB models + migrations`
4. `MCP tools`
5. `workflow engine`
6. `admin/approval UI`
7. `observability + CI`

---

## Risks & Mitigations
- **Risk:** dual-write inconsistencies during migration  
  **Mitigation:** temporary shadow writes + reconciliation job before cutover.

- **Risk:** connector schema drift breaks mappings  
  **Mitigation:** nightly schema diff + contract alerting.

- **Risk:** LLM overconfident on stale data  
  **Mitigation:** mandatory freshness metadata in tool responses; refusal policy when stale.

- **Risk:** write-back side effects  
  **Mitigation:** idempotency + approval queue + per-connector kill switch.

---

## First 3 Tickets to Open Immediately
1. `EVIE-001` — Introduce connector core module + registry and wire startup health.
2. `EVIE-002` — Implement bitemporal base migration + versioned ingestion write path.
3. `EVIE-003` — Build PropexoAdapter read path for resident/lease/property entities.

-- EvieAI bitemporal schema foundation (sketch)
-- Purpose: preserve both business-valid time and system-recorded time
-- for auditability, replay, and immutable decision traces.

BEGIN;

-- Core canonical entity table (example: resident facts)
CREATE TABLE IF NOT EXISTS entity_resident (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,

    -- source lineage
    source_id TEXT NOT NULL,                 -- e.g. propexo, entrata_direct
    source_record_id TEXT NOT NULL,
    source_payload JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- canonical fields
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    phone TEXT,
    lease_status TEXT,

    -- bitemporal validity (business time)
    valid_from TIMESTAMPTZ NOT NULL,
    valid_to TIMESTAMPTZ,

    -- system time (recording lifecycle)
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    superseded_at TIMESTAMPTZ,

    -- trust metadata
    confidence NUMERIC(5,4) NOT NULL DEFAULT 1.0,

    -- dedupe/idempotency helpers
    record_hash TEXT NOT NULL,
    idempotency_key TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_valid_range CHECK (valid_to IS NULL OR valid_to > valid_from),
    CONSTRAINT chk_system_range CHECK (superseded_at IS NULL OR superseded_at > recorded_at),
    CONSTRAINT uq_entity_resident_open UNIQUE (tenant_id, source_id, source_record_id, recorded_at)
);

CREATE INDEX IF NOT EXISTS idx_entity_resident_lookup
    ON entity_resident (tenant_id, source_id, source_record_id);

CREATE INDEX IF NOT EXISTS idx_entity_resident_valid_window
    ON entity_resident (tenant_id, valid_from, valid_to);

CREATE INDEX IF NOT EXISTS idx_entity_resident_system_window
    ON entity_resident (tenant_id, recorded_at, superseded_at);

CREATE INDEX IF NOT EXISTS idx_entity_resident_hash
    ON entity_resident (tenant_id, record_hash);

-- Append-only audit ledger for every read/write/agent action
CREATE TABLE IF NOT EXISTS audit_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    actor_type TEXT NOT NULL,               -- user, system, agent
    actor_id TEXT NOT NULL,
    action_type TEXT NOT NULL,              -- read, write, tool_call, llm_call
    target_type TEXT NOT NULL,              -- entity, connector, workflow
    target_id TEXT,
    request_id TEXT,
    idempotency_key TEXT,

    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    outcome JSONB NOT NULL DEFAULT '{}'::jsonb,

    occurred_at TIMESTAMPTZ NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    prev_hash TEXT,
    event_hash TEXT NOT NULL,

    CONSTRAINT uq_audit_event_hash UNIQUE (event_hash)
);

CREATE INDEX IF NOT EXISTS idx_audit_ledger_tenant_time
    ON audit_ledger (tenant_id, recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_ledger_request
    ON audit_ledger (request_id);

-- Generic pattern for bitemporal upsert:
-- 1) close existing open system record for source record
-- 2) insert new fact row with new valid/system intervals

COMMIT;

-- EvieAI runtime bitemporal schema for connector ingestion (PostgreSQL)
-- Supports Phase 3 backend store + idempotent ingest dedupe.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS ingest_dedupe (
    id BIGSERIAL PRIMARY KEY,
    idempotency_key TEXT UNIQUE NOT NULL,
    source_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS entity_snapshot (
    id BIGSERIAL PRIMARY KEY,
    source_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    canonical_json JSONB NOT NULL,
    payload_json JSONB NOT NULL,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    valid_from TIMESTAMPTZ NOT NULL,
    valid_to TIMESTAMPTZ,
    recorded_at TIMESTAMPTZ NOT NULL,
    superseded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(source_id, entity_type, source_record_id, recorded_at)
);

CREATE INDEX IF NOT EXISTS idx_entity_snapshot_lookup
    ON entity_snapshot(source_id, entity_type, source_record_id, recorded_at DESC);

CREATE TABLE IF NOT EXISTS entity_fact (
    id BIGSERIAL PRIMARY KEY,
    source_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    fact_key TEXT NOT NULL,
    fact_value_json JSONB,
    valid_from TIMESTAMPTZ NOT NULL,
    valid_to TIMESTAMPTZ,
    recorded_at TIMESTAMPTZ NOT NULL,
    superseded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(source_id, entity_type, source_record_id, fact_key, recorded_at)
);

CREATE INDEX IF NOT EXISTS idx_entity_fact_lookup
    ON entity_fact(source_id, entity_type, source_record_id, fact_key, recorded_at DESC);

CREATE TABLE IF NOT EXISTS audit_ledger (
    id BIGSERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,
    source_id TEXT,
    entity_type TEXT,
    source_record_id TEXT,
    payload_json JSONB NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    prev_hash TEXT,
    row_hash TEXT NOT NULL
);

COMMIT;

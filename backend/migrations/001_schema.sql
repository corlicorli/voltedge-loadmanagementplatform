-- ===========================================================================
-- Load Control Context — operational schema
-- Mirrors the domain model 1:1 (aggregate, entities, value objects).
-- ===========================================================================
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Aggregate root: LoadArea
CREATE TABLE IF NOT EXISTS load_areas (
    area_code         TEXT PRIMARY KEY,                          -- AreaCode (VO)
    area_name         TEXT NOT NULL,
    max_capacity_kw   NUMERIC(10, 3) NOT NULL,                   -- MaxCapacity (VO)
    warning_fraction  NUMERIC(5, 4) NOT NULL DEFAULT 0.85,       -- ThresholdPercentage (VO)
    critical_fraction NUMERIC(5, 4) NOT NULL DEFAULT 1.00,       -- ThresholdPercentage (VO)
    status            TEXT NOT NULL DEFAULT 'STABLE'             -- LoadStatus (VO)
                      CHECK (status IN ('STABLE', 'WARNING', 'CRITICAL')),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Entity: Charger
CREATE TABLE IF NOT EXISTS chargers (
    charger_id   TEXT PRIMARY KEY,
    area_code    TEXT NOT NULL REFERENCES load_areas(area_code) ON DELETE CASCADE,
    max_power_kw NUMERIC(10, 3) NOT NULL,
    status       TEXT NOT NULL DEFAULT 'AVAILABLE'
                 CHECK (status IN ('AVAILABLE', 'OCCUPIED', 'FAULTED')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_chargers_area ON chargers(area_code);

-- Entity: ChargingSession
CREATE TABLE IF NOT EXISTS charging_sessions (
    session_id         UUID PRIMARY KEY,
    area_code          TEXT NOT NULL REFERENCES load_areas(area_code) ON DELETE CASCADE,
    charger_id         TEXT NOT NULL REFERENCES chargers(charger_id),
    requested_power_kw NUMERIC(10, 3) NOT NULL,                  -- PowerLevel (VO)
    current_power_kw   NUMERIC(10, 3) NOT NULL,                  -- PowerLevel (VO)
    status             TEXT NOT NULL DEFAULT 'ACTIVE'
                       CHECK (status IN ('ACTIVE', 'STOPPED')),
    started_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    stopped_at         TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_sessions_area_status ON charging_sessions(area_code, status);

-- Entity: LoadRule
CREATE TABLE IF NOT EXISTS load_rules (
    rule_id            UUID PRIMARY KEY,
    area_code          TEXT NOT NULL REFERENCES load_areas(area_code) ON DELETE CASCADE,
    rule_type          TEXT NOT NULL CHECK (rule_type IN ('WARNING_LIMIT', 'CRITICAL_REGULATION')),
    threshold_fraction NUMERIC(5, 4) NOT NULL,
    reduction_fraction NUMERIC(5, 4) NOT NULL,
    active             BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS idx_rules_area ON load_rules(area_code);

-- Entity: LoadAdjustment
CREATE TABLE IF NOT EXISTS load_adjustments (
    adjustment_id     UUID PRIMARY KEY,
    area_code         TEXT NOT NULL REFERENCES load_areas(area_code) ON DELETE CASCADE,
    session_id        UUID NOT NULL,
    previous_power_kw NUMERIC(10, 3) NOT NULL,
    new_power_kw      NUMERIC(10, 3) NOT NULL,
    reason            TEXT NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_adjustments_area_time ON load_adjustments(area_code, created_at DESC);

-- Event store: every domain event (audit trail + projection source)
CREATE TABLE IF NOT EXISTS domain_events (
    id           BIGSERIAL PRIMARY KEY,
    event_id     UUID NOT NULL,
    event_type   TEXT NOT NULL,
    aggregate_id TEXT NOT NULL,
    payload      JSONB NOT NULL,
    occurred_at  TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_aggregate_time ON domain_events(aggregate_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_type_time ON domain_events(event_type, occurred_at DESC);

-- Read model / warehouse fact table: time-series of load samples
CREATE TABLE IF NOT EXISTS load_samples (
    id                    BIGSERIAL PRIMARY KEY,
    area_code             TEXT NOT NULL REFERENCES load_areas(area_code) ON DELETE CASCADE,
    current_load_kw       NUMERIC(10, 3) NOT NULL,
    available_capacity_kw NUMERIC(10, 3) NOT NULL,
    status                TEXT NOT NULL,
    active_session_count  INT NOT NULL,
    sampled_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_samples_area_time ON load_samples(area_code, sampled_at DESC);

-- Manual intervention requests (ManualInterventionPolicy -> ExternalTechnician)
CREATE TABLE IF NOT EXISTS intervention_requests (
    request_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    area_code       TEXT NOT NULL REFERENCES load_areas(area_code) ON DELETE CASCADE,
    reason          TEXT NOT NULL,
    load_kw         NUMERIC(10, 3) NOT NULL,
    max_capacity_kw NUMERIC(10, 3) NOT NULL,
    status          TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'RESOLVED')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_interventions_area ON intervention_requests(area_code, status);

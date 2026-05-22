-- ===========================================================================
-- Seed: LoadArea YN (Ydre Nørrebro) — the scenario from the report.
-- 24 chargers, 240 kW max, baseline ~233 kW (WARNING). Historical load samples
-- (7 days, morning/evening peaks) give the BI dashboard real trend data.
-- This runs once on a fresh database; the live demo generates real data on top.
-- ===========================================================================

-- Aggregate root
INSERT INTO load_areas (area_code, area_name, max_capacity_kw, warning_fraction, critical_fraction, status)
VALUES ('YN', 'Ydre Nørrebro', 240.0, 0.85, 1.00, 'WARNING')
ON CONFLICT (area_code) DO NOTHING;

-- 24 chargers, 11 kW each. YN-01..YN-22 occupied, YN-23..YN-24 free for the demo.
INSERT INTO chargers (charger_id, area_code, max_power_kw, status)
SELECT 'YN-' || lpad(g::text, 2, '0'), 'YN', 11.0,
       CASE WHEN g <= 22 THEN 'OCCUPIED' ELSE 'AVAILABLE' END
FROM generate_series(1, 24) g
ON CONFLICT (charger_id) DO NOTHING;

-- Load rules: CRITICAL regulation (>=100% -> reduce 10%) + a WARNING limit marker.
INSERT INTO load_rules (rule_id, area_code, rule_type, threshold_fraction, reduction_fraction, active)
VALUES
    (gen_random_uuid(), 'YN', 'CRITICAL_REGULATION', 1.00, 0.10, TRUE),
    (gen_random_uuid(), 'YN', 'WARNING_LIMIT',       0.85, 0.00, TRUE);

-- Baseline active sessions: 21 x 11 kW + 1 x 2 kW = 233 kW (status WARNING).
INSERT INTO charging_sessions
    (session_id, area_code, charger_id, requested_power_kw, current_power_kw, status, started_at)
SELECT gen_random_uuid(), 'YN', 'YN-' || lpad(g::text, 2, '0'), 11.0, 11.0, 'ACTIVE',
       now() - (g || ' minutes')::interval
FROM generate_series(1, 21) g;

INSERT INTO charging_sessions
    (session_id, area_code, charger_id, requested_power_kw, current_power_kw, status, started_at)
VALUES (gen_random_uuid(), 'YN', 'YN-22', 2.0, 2.0, 'ACTIVE', now() - interval '22 minutes');

-- Historical load samples: 7 days at 30-min resolution, with morning (~08:00)
-- and evening (~18:30) peaks plus noise. Populates the BI trend/peak/utilisation views.
INSERT INTO load_samples (area_code, current_load_kw, available_capacity_kw, status, active_session_count, sampled_at)
SELECT
    'YN',
    load_kw,
    ROUND(240.0 - load_kw, 3),
    CASE WHEN load_kw >= 240 THEN 'CRITICAL'
         WHEN load_kw >= 204 THEN 'WARNING'
         ELSE 'STABLE' END,
    GREATEST(1, ROUND(load_kw / 11.0)::int),
    ts
FROM (
    SELECT
        ts,
        GREATEST(20, ROUND((
            112
            + 100 * exp(-power((extract(hour FROM ts) + extract(minute FROM ts) / 60.0) - 8.0, 2) / 5.0)
            + 128 * exp(-power((extract(hour FROM ts) + extract(minute FROM ts) / 60.0) - 18.5, 2) / 6.0)
            + (random() * 24 - 12)
        )::numeric, 3)) AS load_kw
    FROM generate_series(now() - interval '7 days', now() - interval '30 minutes', interval '30 minutes') ts
) samples;

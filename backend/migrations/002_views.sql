-- ===========================================================================
-- Read models (event-storming §3.4) + analytics/warehouse views (BI layer).
-- These are the projections the API query side and the React BI dashboard read.
-- ===========================================================================

-- ----- Read models ---------------------------------------------------------

-- LoadAreaStatusView + CurrentLoadView: live status and load for an area.
CREATE OR REPLACE VIEW v_load_area_status AS
SELECT
    la.area_code,
    la.area_name,
    la.max_capacity_kw,
    ROUND(la.max_capacity_kw * la.warning_fraction, 3)  AS warning_threshold_kw,
    ROUND(la.max_capacity_kw * la.critical_fraction, 3) AS critical_threshold_kw,
    COALESCE(SUM(cs.current_power_kw) FILTER (WHERE cs.status = 'ACTIVE'), 0) AS current_load_kw,
    ROUND(
        la.max_capacity_kw - COALESCE(SUM(cs.current_power_kw) FILTER (WHERE cs.status = 'ACTIVE'), 0),
        3
    ) AS available_capacity_kw,
    la.status,
    COUNT(cs.session_id) FILTER (WHERE cs.status = 'ACTIVE') AS active_session_count,
    la.updated_at
FROM load_areas la
LEFT JOIN charging_sessions cs ON cs.area_code = la.area_code
GROUP BY la.area_code;

-- ActiveChargingSessionsView
CREATE OR REPLACE VIEW v_active_sessions AS
SELECT session_id, area_code, charger_id, requested_power_kw, current_power_kw, status, started_at
FROM charging_sessions
WHERE status = 'ACTIVE';

-- ChargerPowerView: how much power each charger currently draws.
CREATE OR REPLACE VIEW v_charger_power AS
SELECT
    c.charger_id,
    c.area_code,
    c.max_power_kw,
    c.status AS charger_status,
    COALESCE(cs.current_power_kw, 0) AS current_power_kw,
    cs.session_id
FROM chargers c
LEFT JOIN charging_sessions cs
    ON cs.charger_id = c.charger_id AND cs.status = 'ACTIVE';

-- LoadAdjustmentView
CREATE OR REPLACE VIEW v_load_adjustments AS
SELECT adjustment_id, area_code, session_id, previous_power_kw, new_power_kw, reason, created_at
FROM load_adjustments;

-- ----- Analytics / warehouse views (BI) ------------------------------------

-- Raw load time-series.
CREATE OR REPLACE VIEW v_load_timeseries AS
SELECT area_code, sampled_at, current_load_kw, available_capacity_kw, status, active_session_count
FROM load_samples;

-- Descriptive: hourly utilisation.
CREATE OR REPLACE VIEW v_load_utilisation_hourly AS
SELECT
    ls.area_code,
    date_trunc('hour', ls.sampled_at) AS hour,
    ROUND(AVG(ls.current_load_kw), 3) AS avg_load_kw,
    ROUND(MAX(ls.current_load_kw), 3) AS peak_load_kw,
    la.max_capacity_kw,
    ROUND(AVG(ls.current_load_kw) / la.max_capacity_kw * 100, 2) AS avg_utilisation_pct,
    ROUND(MAX(ls.current_load_kw) / la.max_capacity_kw * 100, 2) AS peak_utilisation_pct,
    ROUND(AVG(ls.active_session_count), 1) AS avg_sessions
FROM load_samples ls
JOIN load_areas la ON la.area_code = ls.area_code
GROUP BY ls.area_code, date_trunc('hour', ls.sampled_at), la.max_capacity_kw;

-- Descriptive: daily peaks + time spent in each status.
CREATE OR REPLACE VIEW v_peak_loads_daily AS
SELECT
    ls.area_code,
    date_trunc('day', ls.sampled_at) AS day,
    ROUND(MAX(ls.current_load_kw), 3) AS peak_load_kw,
    ROUND(AVG(ls.current_load_kw), 3) AS avg_load_kw,
    la.max_capacity_kw,
    ROUND(MAX(ls.current_load_kw) / la.max_capacity_kw * 100, 2) AS peak_utilisation_pct,
    COUNT(*) FILTER (WHERE ls.status = 'CRITICAL') AS critical_samples,
    COUNT(*) FILTER (WHERE ls.status = 'WARNING') AS warning_samples,
    COUNT(*) FILTER (WHERE ls.status = 'STABLE') AS stable_samples
FROM load_samples ls
JOIN load_areas la ON la.area_code = ls.area_code
GROUP BY ls.area_code, date_trunc('day', ls.sampled_at), la.max_capacity_kw;

-- Diagnostic: regulation-related events from the event store.
CREATE OR REPLACE VIEW v_regulation_events AS
SELECT aggregate_id AS area_code, event_type, occurred_at, payload
FROM domain_events
WHERE event_type IN (
    'LoadThresholdReached', 'LoadRuleActivated', 'RegulationResultEvaluated',
    'LoadAreaStabilized', 'RegulationFailed'
);

-- Diagnostic: event counts per type per day.
CREATE OR REPLACE VIEW v_event_daily_counts AS
SELECT aggregate_id AS area_code, event_type, date_trunc('day', occurred_at) AS day, COUNT(*) AS event_count
FROM domain_events
GROUP BY aggregate_id, event_type, date_trunc('day', occurred_at);

-- Headline KPIs for the BI dashboard.
CREATE OR REPLACE VIEW v_area_kpis AS
SELECT
    s.area_code,
    s.area_name,
    s.current_load_kw,
    s.max_capacity_kw,
    s.available_capacity_kw,
    s.status,
    s.active_session_count,
    ROUND(s.current_load_kw / s.max_capacity_kw * 100, 2) AS current_utilisation_pct,
    (SELECT ROUND(MAX(current_load_kw), 3) FROM load_samples
     WHERE area_code = s.area_code AND sampled_at >= now() - interval '24 hours') AS peak_load_24h_kw,
    (SELECT COUNT(*) FROM load_adjustments WHERE area_code = s.area_code) AS total_adjustments,
    (SELECT COUNT(*) FROM intervention_requests
     WHERE area_code = s.area_code AND status = 'OPEN') AS open_interventions
FROM v_load_area_status s;

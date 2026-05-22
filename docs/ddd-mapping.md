# DDD → Code → Database mapping

This document makes the coupling between the Domain-Driven Design model (report §3) and the
implementation explicit, as required by exam §4 ("a clear link between DDD principles — events,
aggregates, entities, value objects — and ... the data model implemented in the database").

All domain paths are under `backend/app/load_control/`.

## Aggregate root

| Design | Code | Database |
| --- | --- | --- |
| `LoadArea` (aggregate root, transactional boundary, owns all invariants) | `domain/load_area.py` → `class LoadArea` | table `load_areas` |

## Entities

| Design | Code | Database |
| --- | --- | --- |
| `Charger` | `domain/entities.py` → `Charger` | `chargers` |
| `ChargingSession` | `domain/entities.py` → `ChargingSession` | `charging_sessions` |
| `LoadRule` | `domain/entities.py` → `LoadRule` | `load_rules` |
| `LoadAdjustment` | `domain/entities.py` → `LoadAdjustment` | `load_adjustments` |

## Value objects

| Design | Code | Database |
| --- | --- | --- |
| `AreaCode` | `value_objects.py` → `AreaCode` | `load_areas.area_code` |
| `PowerLevel` | `value_objects.py` → `PowerLevel` | `*_power_kw` columns |
| `LoadStatus` (STABLE/WARNING/CRITICAL) | `value_objects.py` → `LoadStatus` | `*.status` (+ CHECK constraint) |
| `ThresholdPercentage` | `value_objects.py` → `ThresholdPercentage` | `load_areas.warning_fraction`, `critical_fraction` |
| `MaxCapacity` / `CurrentLoad` / `AvailableCapacity` | `LoadThresholds` + derived properties on `LoadArea` | `max_capacity_kw`; current/available derived in `v_load_area_status` |

## Domain events (the nine from the event storming)

All defined in `domain/events.py`, recorded by aggregate methods, persisted to `domain_events`
(`event_type`, `payload` JSONB) by `infrastructure/event_publisher.py`. `LoadAreaUpdated` and
`CurrentLoadUpdated` are additionally projected into the `load_samples` time-series.

| Event | Recorded in `LoadArea.` |
| --- | --- |
| `ChargingSessionStarted` | `start_session` |
| `LoadAreaUpdated` | `_update_load` |
| `LoadThresholdReached` | `_evaluate_capacity` |
| `LoadRuleActivated` | `activate_regulation` |
| `ChargingPowerReduced` | `reduce_charging_power` (one per active session) |
| `CurrentLoadUpdated` | `_recalculate` |
| `RegulationResultEvaluated` | `evaluate_regulation_result` |
| `LoadAreaStabilized` | `evaluate_regulation_result` (success) |
| `RegulationFailed` | `evaluate_regulation_result` (failure) |

## Commands

| Design command | Code |
| --- | --- |
| `StartChargingSession` (external) | `application/commands.py` → API `POST /sessions` → `LoadControlService.start_charging_session` |
| `EvaluateLoadAreaCapacity` (external) | `application/commands.py` → API `POST /evaluate` → `LoadControlService.evaluate_capacity` |
| `UpdateCurrentLoad`, `ActivateLoadRule`, `ReduceChargingPower`, `RecalculateCurrentLoad`, `EvaluateRegulationResult`, `MarkLoadStable` (internal) | realised as `LoadArea` methods, orchestrated by the service |
| `CreateInterventionRequest` | `infrastructure/intervention_service.py` → `intervention_requests` |

## Policies (named, from §3.3)

All in `application/policies.py`, invoked in `application/load_control_service.py`.

| Policy | Trigger | Rule |
| --- | --- | --- |
| `LoadRegulationPolicy` | `LoadAreaUpdated` | if load reaches max capacity → activate regulation |
| `PowerReductionPolicy` | `LoadThresholdReached` | if threshold reached → reduce charging power 10% |
| `StabilizationPolicy` | `RegulationResultEvaluated` | if below max → mark area stable |
| `ManualInterventionPolicy` | `RegulationResultEvaluated` | if still above max → create manual intervention request |

## Read models (§3.4) → warehouse views

| Read model | View |
| --- | --- |
| `LoadAreaStatusView` / `CurrentLoadView` | `v_load_area_status` |
| `ActiveChargingSessionsView` | `v_active_sessions` |
| `ChargerPowerView` | `v_charger_power` |
| `LoadAdjustmentView` | `v_load_adjustments` |
| (analytics/BI) | `v_load_utilisation_hourly`, `v_peak_loads_daily`, `v_regulation_events`, `v_event_daily_counts`, `v_area_kpis` |

## Business rules (§3.1)

| Rule | Where enforced |
| --- | --- |
| 1 — `<85%` → STABLE | `LoadThresholds.classify` |
| 2 — `85–100%` → WARNING | `LoadThresholds.classify` |
| 3 — `≥100%` → CRITICAL, reduce power | `classify` + `reduce_charging_power` + `PowerReductionPolicy` |
| 4 — still above max after regulation → incident | `evaluate_regulation_result` + `ManualInterventionPolicy` → `intervention_requests` |
| 5 — `<85%` → restore power | `LoadArea.restore_power_if_stable` |

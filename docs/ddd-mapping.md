# DDD → Code → Database mapping

This document makes the coupling between the Domain-Driven Design model (report §3) and the
implementation explicit, as required by exam §4 ("a clear link between DDD principles — events,
aggregates, entities, value objects — and ... the data model implemented in the database").

All domain paths are under `backend/app/load_control/`.

## Aggregate root

| Design | Code | Database |
| --- | --- | --- |
| `LoadArea` (aggregate root, transactional boundary, owns all invariants) | `domain/load_area.py` → `class LoadArea` | collection `load_areas` (`_id` = area code) |

## Entities

| Design | Code | Database |
| --- | --- | --- |
| `Charger` | `domain/entities.py` → `Charger` | collection `chargers` (`_id` = charger id) |
| `ChargingSession` | `domain/entities.py` → `ChargingSession` | collection `charging_sessions` (`_id` = session uuid) |
| `LoadRule` | `domain/entities.py` → `LoadRule` | collection `load_rules` (`_id` = rule uuid) |
| `LoadAdjustment` | `domain/entities.py` → `LoadAdjustment` | collection `load_adjustments` (`_id` = adjustment uuid) |

## Value objects

| Design | Code | Database |
| --- | --- | --- |
| `AreaCode` | `value_objects.py` → `AreaCode` | `load_areas._id` |
| `PowerLevel` | `value_objects.py` → `PowerLevel` | `*_power_kw` fields |
| `LoadStatus` (STABLE/WARNING/CRITICAL) | `value_objects.py` → `LoadStatus` | `*.status` field |
| `ThresholdPercentage` | `value_objects.py` → `ThresholdPercentage` | `load_areas.warning_fraction`, `critical_fraction` |
| `MaxCapacity` / `CurrentLoad` / `AvailableCapacity` | `LoadThresholds` + derived properties on `LoadArea` | `max_capacity_kw`; current/available derived in the status aggregation (`MongoLoadAreaQueries.status`) |

## Domain events (the nine from the event storming)

All defined in `domain/events.py`, recorded by aggregate methods, persisted to the `domain_events`
collection (`event_type`, `payload`) by `infrastructure/event_publisher.py`. `LoadAreaUpdated` and
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
| `CreateInterventionRequest` | `infrastructure/intervention_service.py` → `intervention_requests` collection |

## Policies (named, from §3.3)

All in `application/policies.py`, invoked in `application/load_control_service.py`.

| Policy | Trigger | Rule |
| --- | --- | --- |
| `LoadRegulationPolicy` | `LoadAreaUpdated` | if load reaches max capacity → activate regulation |
| `PowerReductionPolicy` | `LoadThresholdReached` | if threshold reached → reduce charging power 10% |
| `StabilizationPolicy` | `RegulationResultEvaluated` | if below max → mark area stable |
| `ManualInterventionPolicy` | `RegulationResultEvaluated` | if still above max → create manual intervention request |

## Read models (§3.4) → read-side aggregations

The SQL warehouse views are realised as MongoDB aggregation pipelines / queries on the read side
(CQRS), so the write model (collections) and read model (projections) stay decoupled.

| Read model | Realised by |
| --- | --- |
| `LoadAreaStatusView` / `CurrentLoadView` | `infrastructure/queries.py` → `status` (sum of active sessions) |
| `ActiveChargingSessionsView` | `infrastructure/queries.py` → `active_sessions` |
| `ChargerPowerView` | `infrastructure/queries.py` → `chargers` |
| `LoadAdjustmentView` | `infrastructure/queries.py` → `adjustments` |
| (analytics/BI) | `analytics/.../analytics_service.py` → `hourly_utilisation`, `daily_peaks`, `regulation_events`, `event_counts`, `kpis` (`$group` + `$dateTrunc` pipelines) |

## Business rules (§3.1)

| Rule | Where enforced |
| --- | --- |
| 1 — `<85%` → STABLE | `LoadThresholds.classify` |
| 2 — `85–100%` → WARNING | `LoadThresholds.classify` |
| 3 — `≥100%` → CRITICAL, reduce power | `classify` + `reduce_charging_power` + `PowerReductionPolicy` |
| 4 — still above max after regulation → incident | `evaluate_regulation_result` + `ManualInterventionPolicy` → `intervention_requests` |
| 5 — `<85%` → restore power | `LoadArea.restore_power_if_stable` |

"""Mappers between database rows and the LoadArea aggregate.

This is the explicit domain<->persistence boundary required by the exam: the
domain model never sees a row, and the schema never sees a domain object.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.load_control.domain.entities import (
    Charger,
    ChargerStatus,
    ChargingSession,
    LoadRule,
    LoadRuleType,
    SessionStatus,
)
from app.load_control.domain.load_area import LoadArea
from app.load_control.domain.value_objects import (
    AreaCode,
    LoadStatus,
    LoadThresholds,
    PowerLevel,
    ThresholdPercentage,
)

Row = Any  # asyncpg.Record behaves like a mapping


def to_load_area(
    area: Row,
    charger_rows: Sequence[Row],
    session_rows: Sequence[Row],
    rule_rows: Sequence[Row],
) -> LoadArea:
    thresholds = LoadThresholds(
        max_capacity_kw=area["max_capacity_kw"],
        warning=ThresholdPercentage(area["warning_fraction"]),
        critical=ThresholdPercentage(area["critical_fraction"]),
    )
    chargers = [
        Charger(
            charger_id=r["charger_id"],
            area_code=r["area_code"],
            max_power_kw=r["max_power_kw"],
            status=ChargerStatus(r["status"]),
        )
        for r in charger_rows
    ]
    sessions = [
        ChargingSession(
            session_id=str(r["session_id"]),
            area_code=r["area_code"],
            charger_id=r["charger_id"],
            requested_power=PowerLevel(r["requested_power_kw"]),
            current_power=PowerLevel(r["current_power_kw"]),
            status=SessionStatus(r["status"]),
            started_at=r["started_at"],
            stopped_at=r["stopped_at"],
        )
        for r in session_rows
    ]
    rules = [
        LoadRule(
            rule_id=str(r["rule_id"]),
            area_code=r["area_code"],
            rule_type=LoadRuleType(r["rule_type"]),
            threshold_fraction=r["threshold_fraction"],
            reduction_fraction=r["reduction_fraction"],
            active=r["active"],
        )
        for r in rule_rows
    ]
    return LoadArea(
        area_code=AreaCode(area["area_code"]),
        area_name=area["area_name"],
        thresholds=thresholds,
        chargers=chargers,
        sessions=sessions,
        rules=rules,
        status=LoadStatus(area["status"]),
    )

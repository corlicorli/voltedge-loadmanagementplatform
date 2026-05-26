"""Mappers between MongoDB documents and the LoadArea aggregate.

This is the explicit domain<->persistence boundary required by the exam: the
domain model never sees a document, and the collections never see a domain
object. Each document stores its natural key in `_id`.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
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

Doc = Mapping[str, Any]


def to_load_area(
    area: Doc,
    charger_docs: Sequence[Doc],
    session_docs: Sequence[Doc],
    rule_docs: Sequence[Doc],
) -> LoadArea:
    thresholds = LoadThresholds(
        max_capacity_kw=area["max_capacity_kw"],
        warning=ThresholdPercentage(area["warning_fraction"]),
        critical=ThresholdPercentage(area["critical_fraction"]),
    )
    chargers = [
        Charger(
            charger_id=d["_id"],
            area_code=d["area_code"],
            max_power_kw=d["max_power_kw"],
            name=d.get("name", d["_id"]),
            status=ChargerStatus(d["status"]),
            last_seen_at=d.get("last_seen_at"),
        )
        for d in charger_docs
    ]
    sessions = [
        ChargingSession(
            session_id=d["_id"],
            area_code=d["area_code"],
            charger_id=d["charger_id"],
            requested_power=PowerLevel(d["requested_power_kw"]),
            current_power=PowerLevel(d["current_power_kw"]),
            status=SessionStatus(d["status"]),
            started_at=d["started_at"],
            stopped_at=d.get("stopped_at"),
        )
        for d in session_docs
    ]
    rules = [
        LoadRule(
            rule_id=d["_id"],
            area_code=d["area_code"],
            rule_type=LoadRuleType(d["rule_type"]),
            threshold_fraction=d["threshold_fraction"],
            reduction_fraction=d["reduction_fraction"],
            active=d["active"],
        )
        for d in rule_docs
    ]
    return LoadArea(
        area_code=AreaCode(area["_id"]),
        area_name=area["area_name"],
        thresholds=thresholds,
        chargers=chargers,
        sessions=sessions,
        rules=rules,
        status=LoadStatus(area["status"]),
    )

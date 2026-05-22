"""Analytics API schemas (camelCase output for the React BI dashboard)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class KpiResponse(CamelModel):
    area_code: str
    area_name: str
    current_load_kw: float
    max_capacity_kw: float
    available_capacity_kw: float
    status: str
    active_session_count: int
    current_utilisation_pct: float
    peak_load_24h_kw: float | None = None
    total_adjustments: int
    open_interventions: int


class LoadSamplePoint(CamelModel):
    sampled_at: datetime
    current_load_kw: float
    available_capacity_kw: float
    status: str
    active_session_count: int


class HourlyUtilisation(CamelModel):
    hour: datetime
    avg_load_kw: float
    peak_load_kw: float
    avg_utilisation_pct: float
    peak_utilisation_pct: float
    avg_sessions: float


class DailyPeak(CamelModel):
    day: datetime
    peak_load_kw: float
    avg_load_kw: float
    peak_utilisation_pct: float
    critical_samples: int
    warning_samples: int
    stable_samples: int


class StatusDistribution(CamelModel):
    status: str
    samples: int
    pct: float


class RegulationEvent(CamelModel):
    event_type: str
    occurred_at: datetime
    payload: dict[str, Any]


class EventCount(CamelModel):
    event_type: str
    day: datetime
    event_count: int

"""API schemas (Pydantic). Field names are snake_case in code but serialize as
camelCase to match the API model in the report (currentLoadKw, maxCapacityKw, ...).
Input validation here is the system boundary check required by the coding rules.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class CreateLoadAreaRequest(CamelModel):
    area_code: str = Field(min_length=1, examples=["YN"])
    area_name: str = Field(min_length=1, examples=["Ydre Nørrebro"])
    max_capacity_kw: float = Field(gt=0, le=100000, examples=[240])
    warning_fraction: float = Field(default=0.85, gt=0, le=2)
    critical_fraction: float = Field(default=1.00, gt=0, le=2)
    reduction_fraction: float = Field(default=0.10, ge=0, lt=1)


class AreaSummary(CamelModel):
    area_code: str
    area_name: str
    max_capacity_kw: float
    status: str


class StartSessionRequest(CamelModel):
    charger_id: str = Field(min_length=1, examples=["YN-22"])
    power_level_kw: float = Field(gt=0, le=350, examples=[11])


class AreaStatusResponse(CamelModel):
    area_code: str
    area_name: str
    current_load_kw: float
    max_capacity_kw: float
    warning_threshold_kw: float
    critical_threshold_kw: float
    available_capacity_kw: float
    status: str
    active_session_count: int
    updated_at: datetime


class StartSessionResponse(CamelModel):
    session_id: str
    area_status: AreaStatusResponse


class SessionResponse(CamelModel):
    session_id: str
    charger_id: str
    requested_power_kw: float
    current_power_kw: float
    status: str
    started_at: datetime


class AdjustmentResponse(CamelModel):
    adjustment_id: str
    session_id: str
    previous_power_kw: float
    new_power_kw: float
    reason: str
    created_at: datetime


class RegisterChargerRequest(CamelModel):
    charger_id: str = Field(min_length=1, examples=["YN-25"])
    max_power_kw: float = Field(gt=0, le=350, examples=[11])
    name: str = Field(default="", examples=["Nørrebro P1"])


class ChargerResponse(CamelModel):
    charger_id: str
    area_code: str
    name: str
    max_power_kw: float
    occupancy_status: str
    connectivity: str
    current_output_kw: float

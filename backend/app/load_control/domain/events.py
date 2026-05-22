"""The nine domain events of the Load Control Context (from the event storming).

Each event is an immutable fact. The aggregate records them; the application
layer publishes them after the transaction commits.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.shared.domain_event import DomainEvent


@dataclass(frozen=True)
class ChargingSessionStarted(DomainEvent):
    """A charge has started in a LoadArea."""

    area_code: str
    session_id: str
    charger_id: str
    power_kw: float


@dataclass(frozen=True)
class LoadAreaUpdated(DomainEvent):
    """The area's total load has been recomputed."""

    area_code: str
    current_load_kw: float
    available_capacity_kw: float
    status: str
    active_session_count: int


@dataclass(frozen=True)
class LoadThresholdReached(DomainEvent):
    """The load limit has been reached or exceeded."""

    area_code: str
    current_load_kw: float
    threshold_kw: float
    status: str


@dataclass(frozen=True)
class LoadRuleActivated(DomainEvent):
    """A load rule has been activated in response to a threshold."""

    area_code: str
    rule_id: str
    rule_type: str
    reduction_pct: float


@dataclass(frozen=True)
class ChargingPowerReduced(DomainEvent):
    """Charging power has been reduced on an active session."""

    area_code: str
    session_id: str
    previous_power_kw: float
    new_power_kw: float


@dataclass(frozen=True)
class CurrentLoadUpdated(DomainEvent):
    """Load has been recalculated after a regulation step."""

    area_code: str
    current_load_kw: float
    available_capacity_kw: float
    status: str
    active_session_count: int


@dataclass(frozen=True)
class RegulationResultEvaluated(DomainEvent):
    """The outcome of regulation has been assessed."""

    area_code: str
    current_load_kw: float
    max_capacity_kw: float
    success: bool
    rounds: int


@dataclass(frozen=True)
class LoadAreaStabilized(DomainEvent):
    """Load is back below max capacity — the area is stable."""

    area_code: str
    current_load_kw: float
    status: str


@dataclass(frozen=True)
class RegulationFailed(DomainEvent):
    """Automatic regulation did not bring load below max capacity."""

    area_code: str
    current_load_kw: float
    max_capacity_kw: float


@dataclass(frozen=True)
class ChargerRegistered(DomainEvent):
    """A new charger has been registered in a LoadArea."""

    area_code: str
    charger_id: str
    max_power_kw: float

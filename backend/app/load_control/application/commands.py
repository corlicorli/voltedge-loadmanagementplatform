"""Commands — explicit intentions to change the system's state.

These are the externally-triggered commands exposed by the API. The remaining
event-storming commands (UpdateCurrentLoad, ActivateLoadRule, ReduceChargingPower,
RecalculateCurrentLoad, EvaluateRegulationResult, MarkLoadStable) are realized as
methods on the LoadArea aggregate and orchestrated by the named policies.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CreateLoadArea:
    """Trigger/actor: an operator (customer) registers a new load area."""

    area_code: str
    area_name: str
    max_capacity_kw: float
    warning_fraction: float = 0.85
    critical_fraction: float = 1.00
    reduction_fraction: float = 0.10


@dataclass(frozen=True)
class StartChargingSession:
    """Trigger/actor: a user connects a vehicle to a charger."""

    area_code: str
    charger_id: str
    power_kw: float


@dataclass(frozen=True)
class EvaluateLoadAreaCapacity:
    """Trigger: operational re-evaluation of an area's load (and regulate if needed)."""

    area_code: str


@dataclass(frozen=True)
class RegisterCharger:
    """Trigger: a new charger is added to a load area."""

    area_code: str
    charger_id: str
    max_power_kw: float

"""Commands — explicit intentions to change the system's state.

These are the externally-triggered commands exposed by the API. The remaining
event-storming commands (UpdateCurrentLoad, ActivateLoadRule, ReduceChargingPower,
RecalculateCurrentLoad, EvaluateRegulationResult, MarkLoadStable) are realized as
methods on the LoadArea aggregate and orchestrated by the named policies.
"""
from __future__ import annotations

from dataclasses import dataclass


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

"""Entities of the Load Control Context.

Entities have identity and a lifecycle inside the LoadArea aggregate. They are
modelled as frozen dataclasses; state transitions return new instances (same
identity) to preserve immutability, and the aggregate swaps the old for the new.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum

from app.load_control.domain.value_objects import PowerLevel


class ChargerStatus(str, Enum):
    """Occupancy — whether a charger is currently serving a vehicle."""

    AVAILABLE = "AVAILABLE"
    OCCUPIED = "OCCUPIED"
    FAULTED = "FAULTED"


class ChargerConnectivity(str, Enum):
    """Reachability — whether a charger is in contact (derived from its heartbeat)."""

    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"


class SessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    STOPPED = "STOPPED"


class LoadRuleType(str, Enum):
    WARNING_LIMIT = "WARNING_LIMIT"
    CRITICAL_REGULATION = "CRITICAL_REGULATION"


# A charger is considered OFFLINE once its last heartbeat is older than this.
CHARGER_OFFLINE_AFTER_SECONDS = 60


def connectivity_for(last_seen_at: datetime | None, now: datetime) -> ChargerConnectivity:
    """Derive ONLINE/OFFLINE from the time since the last heartbeat."""
    if last_seen_at is None:
        return ChargerConnectivity.OFFLINE
    age_seconds = (now - last_seen_at).total_seconds()
    if age_seconds <= CHARGER_OFFLINE_AFTER_SECONDS:
        return ChargerConnectivity.ONLINE
    return ChargerConnectivity.OFFLINE


@dataclass(frozen=True, slots=True)
class Charger:
    """A physical charging station tied to a LoadArea (own identity + lifecycle)."""

    charger_id: str
    area_code: str
    max_power_kw: float
    name: str = ""
    status: ChargerStatus = ChargerStatus.AVAILABLE
    last_seen_at: datetime | None = None

    def with_heartbeat(self, now: datetime) -> Charger:
        """Return a copy that has just reported in — refreshes last_seen_at."""
        return replace(self, last_seen_at=now)

    def connectivity(self, now: datetime) -> ChargerConnectivity:
        return connectivity_for(self.last_seen_at, now)


@dataclass(frozen=True, slots=True)
class ChargingSession:
    """An active charge between a vehicle and a Charger; drives currentLoad."""

    session_id: str
    area_code: str
    charger_id: str
    requested_power: PowerLevel
    current_power: PowerLevel
    status: SessionStatus
    started_at: datetime
    stopped_at: datetime | None = None

    def reduce_power(self, fraction: float) -> ChargingSession:
        """Return a copy with current_power reduced by `fraction` (a LoadAdjustment)."""
        return replace(self, current_power=self.current_power.reduced_by(fraction))

    def restore_power(self) -> ChargingSession:
        """Return a copy charging again at its requested power (Business Rule 5)."""
        return replace(self, current_power=self.requested_power)

    @property
    def is_active(self) -> bool:
        return self.status == SessionStatus.ACTIVE


@dataclass(frozen=True, slots=True)
class LoadRule:
    """Defines when and how the system regulates (e.g. load >= 100% -> reduce 10%)."""

    rule_id: str
    area_code: str
    rule_type: LoadRuleType
    threshold_fraction: float
    reduction_fraction: float
    active: bool = True


@dataclass(frozen=True, slots=True)
class LoadAdjustment:
    """A concrete regulation of charging power on a single session."""

    adjustment_id: str
    area_code: str
    session_id: str
    previous_power_kw: float
    new_power_kw: float
    reason: str
    created_at: datetime

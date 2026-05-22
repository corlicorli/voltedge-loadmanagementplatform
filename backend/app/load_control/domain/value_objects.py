"""Value Objects for the Load Control Context.

Value objects are identified solely by their value (no identity) and are
immutable (frozen dataclasses). They encode the Ubiquitous Language:
AreaCode, PowerLevel, LoadStatus, ThresholdPercentage and the LoadThresholds
that classify a load into a status (Business Rules 1-3).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class LoadStatus(str, Enum):
    """Operational status of a LoadArea relative to its thresholds."""

    STABLE = "STABLE"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True, slots=True)
class AreaCode:
    """Short code that uniquely identifies a LoadArea (e.g. 'YN')."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("AreaCode must not be empty")
        object.__setattr__(self, "value", self.value.strip().upper())

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class PowerLevel:
    """A quantity of electrical power in kW (e.g. a session's charging power)."""

    kw: float

    def __post_init__(self) -> None:
        if self.kw < 0:
            raise ValueError("PowerLevel cannot be negative")

    def reduced_by(self, fraction: float) -> PowerLevel:
        """Return a NEW PowerLevel reduced by `fraction` (0..1). Immutable."""
        if not 0 <= fraction <= 1:
            raise ValueError("reduction fraction must be between 0 and 1")
        return PowerLevel(round(self.kw * (1 - fraction), 3))


@dataclass(frozen=True, slots=True)
class ThresholdPercentage:
    """A threshold as a fraction of max capacity (e.g. 0.85 == 85%)."""

    fraction: float

    def __post_init__(self) -> None:
        if not 0 < self.fraction <= 2:
            raise ValueError("threshold fraction out of range (0, 2]")

    @property
    def as_percent(self) -> float:
        return round(self.fraction * 100, 2)


@dataclass(frozen=True, slots=True)
class LoadThresholds:
    """Capacity limits for a LoadArea plus the status-classification rules.

    Encodes Business Rules 1-3:
      - currentLoad < 85% of max          -> STABLE
      - 85% <= currentLoad < 100% of max  -> WARNING
      - currentLoad >= 100% of max        -> CRITICAL
    """

    max_capacity_kw: float
    warning: ThresholdPercentage = field(default_factory=lambda: ThresholdPercentage(0.85))
    critical: ThresholdPercentage = field(default_factory=lambda: ThresholdPercentage(1.00))

    @property
    def warning_threshold_kw(self) -> float:
        return round(self.max_capacity_kw * self.warning.fraction, 3)

    @property
    def critical_threshold_kw(self) -> float:
        return round(self.max_capacity_kw * self.critical.fraction, 3)

    def classify(self, current_load_kw: float) -> LoadStatus:
        if current_load_kw >= self.critical_threshold_kw:
            return LoadStatus.CRITICAL
        if current_load_kw >= self.warning_threshold_kw:
            return LoadStatus.WARNING
        return LoadStatus.STABLE

    def available_capacity_kw(self, current_load_kw: float) -> float:
        return round(self.max_capacity_kw - current_load_kw, 3)

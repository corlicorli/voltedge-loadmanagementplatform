"""Application ports (outbound). Implemented by infrastructure adapters."""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.shared.domain_event import DomainEvent


class EventPublisher(ABC):
    """Publishes domain events: persists them to the event store and projects
    load-affecting events into the load_samples read model."""

    @abstractmethod
    async def publish(self, events: list[DomainEvent]) -> None:
        ...


class InterventionService(ABC):
    """Raises a manual intervention request for an external technician
    (the ManualInterventionPolicy outcome)."""

    @abstractmethod
    async def open_request(
        self, area_code: str, reason: str, load_kw: float, max_capacity_kw: float
    ) -> None:
        ...

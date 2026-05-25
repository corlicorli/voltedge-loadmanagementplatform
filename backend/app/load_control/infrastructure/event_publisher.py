"""Persists domain events to the event store and projects load-affecting events
into the load_samples read model (the BI/analytics time-series)."""
from __future__ import annotations

from dataclasses import asdict, fields

from app.load_control.application.ports import EventPublisher
from app.platform.database import Database
from app.shared.domain_event import DomainEvent

# Events that represent a load snapshot worth recording as a time-series sample.
_SAMPLE_EVENTS = {"LoadAreaUpdated", "CurrentLoadUpdated"}
_META_FIELDS = {"event_id", "occurred_at"}


def _payload(event: DomainEvent) -> dict:
    data = asdict(event)
    return {f.name: data[f.name] for f in fields(event) if f.name not in _META_FIELDS}


class MongoEventPublisher(EventPublisher):
    def __init__(self, db: Database) -> None:
        self._db = db

    async def publish(self, events: list[DomainEvent]) -> None:
        if not events:
            return
        event_docs: list[dict] = []
        sample_docs: list[dict] = []
        for event in events:
            payload = _payload(event)
            event_docs.append(
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "aggregate_id": payload["area_code"],
                    "payload": payload,
                    "occurred_at": event.occurred_at,
                }
            )
            if event.event_type in _SAMPLE_EVENTS:
                sample_docs.append(
                    {
                        "area_code": payload["area_code"],
                        "current_load_kw": payload["current_load_kw"],
                        "available_capacity_kw": payload["available_capacity_kw"],
                        "status": payload["status"],
                        "active_session_count": payload["active_session_count"],
                        "sampled_at": event.occurred_at,
                    }
                )
        await self._db.domain_events.insert_many(event_docs)
        if sample_docs:
            await self._db.load_samples.insert_many(sample_docs)

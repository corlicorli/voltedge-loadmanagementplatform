"""Persists domain events to the event store and projects load-affecting
events into the load_samples read model (the BI/analytics time-series)."""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, fields

import asyncpg

from app.load_control.application.ports import EventPublisher
from app.shared.domain_event import DomainEvent

# Events that represent a load snapshot worth recording as a time-series sample.
_SAMPLE_EVENTS = {"LoadAreaUpdated", "CurrentLoadUpdated"}
_META_FIELDS = {"event_id", "occurred_at"}


def _payload(event: DomainEvent) -> dict:
    data = asdict(event)
    return {f.name: data[f.name] for f in fields(event) if f.name not in _META_FIELDS}


class PostgresEventPublisher(EventPublisher):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def publish(self, events: list[DomainEvent]) -> None:
        if not events:
            return
        async with self._pool.acquire() as conn, conn.transaction():
            for event in events:
                payload = _payload(event)
                await conn.execute(
                    """
                    INSERT INTO domain_events
                        (event_id, event_type, aggregate_id, payload, occurred_at)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    uuid.UUID(event.event_id),
                    event.event_type,
                    payload["area_code"],
                    json.dumps(payload),
                    event.occurred_at,
                )
                if event.event_type in _SAMPLE_EVENTS:
                    await conn.execute(
                        """
                        INSERT INTO load_samples
                            (area_code, current_load_kw, available_capacity_kw,
                             status, active_session_count, sampled_at)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        """,
                        payload["area_code"],
                        payload["current_load_kw"],
                        payload["available_capacity_kw"],
                        payload["status"],
                        payload["active_session_count"],
                        event.occurred_at,
                    )

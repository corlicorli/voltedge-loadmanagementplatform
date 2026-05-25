"""Persists manual intervention requests (the ManualInterventionPolicy outcome)."""
from __future__ import annotations

import uuid

from app.load_control.application.ports import InterventionService
from app.platform.database import Database, utcnow


class MongoInterventionService(InterventionService):
    def __init__(self, db: Database) -> None:
        self._db = db

    async def open_request(
        self, area_code: str, reason: str, load_kw: float, max_capacity_kw: float
    ) -> None:
        await self._db.intervention_requests.insert_one(
            {
                "_id": str(uuid.uuid4()),
                "area_code": area_code,
                "reason": reason,
                "load_kw": load_kw,
                "max_capacity_kw": max_capacity_kw,
                "status": "OPEN",
                "created_at": utcnow(),
            }
        )

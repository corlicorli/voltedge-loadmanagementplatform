"""Read-side implementation (CQRS): serves queries by computing the live
projections directly from the MongoDB collections — the document-database
equivalents of the SQL read-model views (v_load_area_status, v_active_sessions,
v_load_adjustments)."""
from __future__ import annotations

from typing import Any

from app.load_control.application.queries import LoadAreaQueries
from app.platform.database import Database


def _round(value: float, ndigits: int = 3) -> float:
    return round(float(value), ndigits)


class MongoLoadAreaQueries(LoadAreaQueries):
    def __init__(self, db: Database) -> None:
        self._db = db

    async def list_areas(self) -> list[dict[str, Any]]:
        docs = await self._db.load_areas.find().sort("_id", 1).to_list(length=None)
        return [
            {
                "area_code": d["_id"],
                "area_name": d["area_name"],
                "max_capacity_kw": d["max_capacity_kw"],
                "status": d["status"],
            }
            for d in docs
        ]

    async def status(self, area_code: str) -> dict[str, Any] | None:
        area = await self._db.load_areas.find_one({"_id": area_code})
        if area is None:
            return None
        agg = await self._db.charging_sessions.aggregate(
            [
                {"$match": {"area_code": area_code, "status": "ACTIVE"}},
                {
                    "$group": {
                        "_id": None,
                        "current_load_kw": {"$sum": "$current_power_kw"},
                        "active_session_count": {"$sum": 1},
                    }
                },
            ]
        ).to_list(length=1)
        current_load = agg[0]["current_load_kw"] if agg else 0.0
        active_count = agg[0]["active_session_count"] if agg else 0
        max_cap = area["max_capacity_kw"]
        return {
            "area_code": area["_id"],
            "area_name": area["area_name"],
            "max_capacity_kw": max_cap,
            "warning_threshold_kw": _round(max_cap * area["warning_fraction"]),
            "critical_threshold_kw": _round(max_cap * area["critical_fraction"]),
            "current_load_kw": _round(current_load),
            "available_capacity_kw": _round(max_cap - current_load),
            "status": area["status"],
            "active_session_count": active_count,
            "updated_at": area.get("updated_at"),
        }

    async def active_sessions(self, area_code: str) -> list[dict[str, Any]]:
        docs = (
            await self._db.charging_sessions.find({"area_code": area_code, "status": "ACTIVE"})
            .sort("started_at", 1)
            .to_list(length=None)
        )
        return [
            {
                "session_id": d["_id"],
                "charger_id": d["charger_id"],
                "requested_power_kw": d["requested_power_kw"],
                "current_power_kw": d["current_power_kw"],
                "status": d["status"],
                "started_at": d["started_at"],
            }
            for d in docs
        ]

    async def adjustments(self, area_code: str, limit: int = 100) -> list[dict[str, Any]]:
        docs = (
            await self._db.load_adjustments.find({"area_code": area_code})
            .sort("created_at", -1)
            .limit(limit)
            .to_list(length=None)
        )
        return [
            {
                "adjustment_id": d["_id"],
                "session_id": d["session_id"],
                "previous_power_kw": d["previous_power_kw"],
                "new_power_kw": d["new_power_kw"],
                "reason": d["reason"],
                "created_at": d["created_at"],
            }
            for d in docs
        ]

    async def chargers(self, area_code: str) -> list[dict[str, Any]]:
        docs = (
            await self._db.chargers.find({"area_code": area_code})
            .sort("_id", 1)
            .to_list(length=None)
        )
        return [
            {
                "charger_id": d["_id"],
                "area_code": d["area_code"],
                "max_power_kw": d["max_power_kw"],
                "status": d["status"],
            }
            for d in docs
        ]

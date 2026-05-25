"""MongoDB implementation of the LoadAreaRepository port (Motor async driver).

Documents are keyed by their natural id (`_id`): area_code, charger_id,
session_id (uuid str), rule_id (uuid str), adjustment_id (uuid str). All access
goes through the bound collection accessors on the Database singleton, and all
filters use field equality — there is no string-built query to inject into.
"""
from __future__ import annotations

from app.load_control.domain.load_area import LoadArea
from app.load_control.domain.repository import LoadAreaNotFound, LoadAreaRepository
from app.load_control.domain.value_objects import AreaCode
from app.load_control.infrastructure.mappers import to_load_area
from app.platform.database import Database, utcnow


class MongoLoadAreaRepository(LoadAreaRepository):
    def __init__(self, db: Database) -> None:
        self._db = db

    async def get(self, area_code: AreaCode) -> LoadArea:
        area = await self._db.load_areas.find_one({"_id": area_code.value})
        if area is None:
            raise LoadAreaNotFound(area_code.value)
        chargers = (
            await self._db.chargers.find({"area_code": area_code.value})
            .sort("_id", 1)
            .to_list(length=None)
        )
        sessions = await self._db.charging_sessions.find(
            {"area_code": area_code.value, "status": "ACTIVE"}
        ).to_list(length=None)
        rules = await self._db.load_rules.find({"area_code": area_code.value}).to_list(
            length=None
        )
        return to_load_area(area, chargers, sessions, rules)

    async def save(self, area: LoadArea) -> None:
        now = utcnow()
        await self._db.load_areas.update_one(
            {"_id": area.area_code.value},
            {
                "$set": {"status": area.status.value, "updated_at": now},
                "$setOnInsert": {
                    "area_name": area.area_name,
                    "max_capacity_kw": area.thresholds.max_capacity_kw,
                    "warning_fraction": area.thresholds.warning.fraction,
                    "critical_fraction": area.thresholds.critical.fraction,
                },
            },
            upsert=True,
        )
        for rule in area.rules:
            await self._db.load_rules.update_one(
                {"_id": rule.rule_id},
                {
                    "$set": {
                        "area_code": rule.area_code,
                        "rule_type": rule.rule_type.value,
                        "threshold_fraction": rule.threshold_fraction,
                        "reduction_fraction": rule.reduction_fraction,
                        "active": rule.active,
                    }
                },
                upsert=True,
            )
        for charger in area.chargers:
            await self._db.chargers.update_one(
                {"_id": charger.charger_id},
                {
                    "$set": {
                        "area_code": charger.area_code,
                        "max_power_kw": charger.max_power_kw,
                        "status": charger.status.value,
                    },
                    "$setOnInsert": {"created_at": now},
                },
                upsert=True,
            )
        for session in area.sessions:
            await self._db.charging_sessions.update_one(
                {"_id": session.session_id},
                {
                    "$set": {
                        "current_power_kw": session.current_power.kw,
                        "status": session.status.value,
                        "stopped_at": session.stopped_at,
                    },
                    "$setOnInsert": {
                        "area_code": session.area_code,
                        "charger_id": session.charger_id,
                        "requested_power_kw": session.requested_power.kw,
                        "started_at": session.started_at,
                    },
                },
                upsert=True,
            )
        for adj in area.adjustments:
            await self._db.load_adjustments.update_one(
                {"_id": adj.adjustment_id},
                {
                    "$setOnInsert": {
                        "area_code": adj.area_code,
                        "session_id": adj.session_id,
                        "previous_power_kw": adj.previous_power_kw,
                        "new_power_kw": adj.new_power_kw,
                        "reason": adj.reason,
                        "created_at": adj.created_at,
                    }
                },
                upsert=True,
            )

    async def exists(self, area_code: AreaCode) -> bool:
        count = await self._db.load_areas.count_documents({"_id": area_code.value}, limit=1)
        return count > 0

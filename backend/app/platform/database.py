"""MongoDB connection layer (Motor async driver).

Replaces the previous PostgreSQL/asyncpg layer. A single `db` singleton owns the
AsyncIOMotorClient and exposes named collection accessors plus lifecycle helpers
(index creation, a one-time demo seed, and a health ping).

The same code talks to a local `mongo:7` container in development and to MongoDB
Atlas (mongodb+srv://...) in the cloud — only MONGO_URL changes.
"""
from __future__ import annotations

import logging
import math
import random
import re
import uuid
from datetime import UTC, datetime, timedelta

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)

from app.platform.config import settings

logger = logging.getLogger("voltedge.db")


def utcnow() -> datetime:
    return datetime.now(UTC)


def redacted_url(url: str | None = None) -> str:
    """Mask the password in a Mongo URL so it is safe to log."""
    return re.sub(r"://([^:/@]+):([^@]+)@", r"://\1:***@", url or settings.mongo_url)


# Demo scenario constants — LoadArea YN (Ydre Nørrebro), from the report.
_AREA_CODE = "YN"
_MAX_CAPACITY_KW = 240.0
_CHARGER_COUNT = 24
_CHARGER_POWER_KW = 11.0


class Database:
    """Owns the Mongo client and exposes named collections + lifecycle helpers."""

    def __init__(self) -> None:
        self._client: AsyncIOMotorClient | None = None

    # ----- lifecycle --------------------------------------------------------

    async def connect(self) -> None:
        self._client = AsyncIOMotorClient(
            settings.mongo_url,
            serverSelectionTimeoutMS=5000,
            tz_aware=True,
            tzinfo=UTC,
            uuidRepresentation="standard",
        )
        logger.info("mongo client created url=%s db=%s", redacted_url(), settings.mongo_db)

    async def disconnect(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    async def ping(self) -> bool:
        try:
            await self.client.admin.command("ping")
            return True
        except Exception:  # noqa: BLE001 - a health check must never raise
            logger.warning("mongo ping failed for %s", redacted_url())
            return False

    # ----- accessors --------------------------------------------------------

    @property
    def client(self) -> AsyncIOMotorClient:
        if self._client is None:
            raise RuntimeError("Mongo client is not initialised; call connect() first")
        return self._client

    @property
    def database(self) -> AsyncIOMotorDatabase:
        return self.client[settings.mongo_db]

    @property
    def load_areas(self) -> AsyncIOMotorCollection:
        return self.database["load_areas"]

    @property
    def chargers(self) -> AsyncIOMotorCollection:
        return self.database["chargers"]

    @property
    def charging_sessions(self) -> AsyncIOMotorCollection:
        return self.database["charging_sessions"]

    @property
    def load_rules(self) -> AsyncIOMotorCollection:
        return self.database["load_rules"]

    @property
    def load_adjustments(self) -> AsyncIOMotorCollection:
        return self.database["load_adjustments"]

    @property
    def domain_events(self) -> AsyncIOMotorCollection:
        return self.database["domain_events"]

    @property
    def load_samples(self) -> AsyncIOMotorCollection:
        return self.database["load_samples"]

    @property
    def intervention_requests(self) -> AsyncIOMotorCollection:
        return self.database["intervention_requests"]

    # ----- indexes ----------------------------------------------------------

    async def init_indexes(self) -> None:
        await self.chargers.create_index("area_code")
        await self.charging_sessions.create_index([("area_code", 1), ("status", 1)])
        await self.charging_sessions.create_index("started_at")
        await self.load_rules.create_index("area_code")
        await self.load_adjustments.create_index([("area_code", 1), ("created_at", -1)])
        await self.domain_events.create_index([("aggregate_id", 1), ("occurred_at", -1)])
        await self.domain_events.create_index([("event_type", 1), ("occurred_at", -1)])
        await self.load_samples.create_index([("area_code", 1), ("sampled_at", -1)])
        await self.intervention_requests.create_index([("area_code", 1), ("status", 1)])
        logger.info("mongo indexes ensured")

    # ----- seed -------------------------------------------------------------

    async def seed(self) -> None:
        """Insert the YN demo area + chargers + baseline sessions + rules + 7 days
        of load samples, but only when the database is empty (runs once)."""
        if await self.load_areas.count_documents({}, limit=1) > 0:
            logger.info("seed skipped: load area(s) already present")
            return

        now = utcnow()
        await self.load_areas.insert_one(
            {
                "_id": _AREA_CODE,
                "area_name": "Ydre Nørrebro",
                "max_capacity_kw": _MAX_CAPACITY_KW,
                "warning_fraction": 0.85,
                "critical_fraction": 1.00,
                "status": "WARNING",
                "updated_at": now,
            }
        )
        # 24 chargers, 11 kW each. YN-01..YN-22 OCCUPIED, YN-23..YN-24 AVAILABLE.
        await self.chargers.insert_many(
            [
                {
                    "_id": f"{_AREA_CODE}-{g:02d}",
                    "area_code": _AREA_CODE,
                    "max_power_kw": _CHARGER_POWER_KW,
                    "status": "OCCUPIED" if g <= 22 else "AVAILABLE",
                    "created_at": now,
                }
                for g in range(1, _CHARGER_COUNT + 1)
            ]
        )
        # Load rules: CRITICAL regulation (>=100% -> reduce 10%) + a WARNING marker.
        await self.load_rules.insert_many(
            [
                {
                    "_id": str(uuid.uuid4()),
                    "area_code": _AREA_CODE,
                    "rule_type": "CRITICAL_REGULATION",
                    "threshold_fraction": 1.00,
                    "reduction_fraction": 0.10,
                    "active": True,
                },
                {
                    "_id": str(uuid.uuid4()),
                    "area_code": _AREA_CODE,
                    "rule_type": "WARNING_LIMIT",
                    "threshold_fraction": 0.85,
                    "reduction_fraction": 0.00,
                    "active": True,
                },
            ]
        )
        # Baseline active sessions: 21 x 11 kW + 1 x 2 kW = 233 kW (status WARNING).
        sessions = [
            {
                "_id": str(uuid.uuid4()),
                "area_code": _AREA_CODE,
                "charger_id": f"{_AREA_CODE}-{g:02d}",
                "requested_power_kw": _CHARGER_POWER_KW,
                "current_power_kw": _CHARGER_POWER_KW,
                "status": "ACTIVE",
                "started_at": now - timedelta(minutes=g),
                "stopped_at": None,
            }
            for g in range(1, 22)
        ]
        sessions.append(
            {
                "_id": str(uuid.uuid4()),
                "area_code": _AREA_CODE,
                "charger_id": f"{_AREA_CODE}-22",
                "requested_power_kw": 2.0,
                "current_power_kw": 2.0,
                "status": "ACTIVE",
                "started_at": now - timedelta(minutes=22),
                "stopped_at": None,
            }
        )
        await self.charging_sessions.insert_many(sessions)
        await self.load_samples.insert_many(self._historical_samples(now))
        logger.info(
            "seed applied: area %s + %s chargers + %s sessions",
            _AREA_CODE,
            _CHARGER_COUNT,
            len(sessions),
        )

    @staticmethod
    def _historical_samples(now: datetime) -> list[dict]:
        """7 days at 30-min resolution with morning (~08:00) and evening (~18:30)
        peaks plus noise — mirrors the SQL seed that feeds the BI trend views."""
        samples: list[dict] = []
        cursor = now - timedelta(days=7)
        end = now - timedelta(minutes=30)
        while cursor <= end:
            hour = cursor.hour + cursor.minute / 60.0
            load = (
                112
                + 100 * math.exp(-((hour - 8.0) ** 2) / 5.0)
                + 128 * math.exp(-((hour - 18.5) ** 2) / 6.0)
                + (random.random() * 24 - 12)  # noqa: S311 - demo noise, not crypto
            )
            load_kw = round(max(20.0, load), 3)
            status = (
                "CRITICAL" if load_kw >= 240 else "WARNING" if load_kw >= 204 else "STABLE"
            )
            samples.append(
                {
                    "area_code": _AREA_CODE,
                    "current_load_kw": load_kw,
                    "available_capacity_kw": round(_MAX_CAPACITY_KW - load_kw, 3),
                    "status": status,
                    "active_session_count": max(1, round(load_kw / _CHARGER_POWER_KW)),
                    "sampled_at": cursor,
                }
            )
            cursor += timedelta(minutes=30)
        return samples


db = Database()

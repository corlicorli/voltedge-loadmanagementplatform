"""MongoDB connection layer (Motor async driver).

A single `db` singleton owns the AsyncIOMotorClient and exposes named collection
accessors plus lifecycle helpers (index creation and a health ping). The system
starts EMPTY — there is no seeding; the demo data is built up through the API
(onboarding + the demo populator), so the running system reflects real usage.

The same code talks to a local `mongo:7` container in development and to MongoDB
Atlas (mongodb+srv://...) in the cloud — only MONGO_URL changes.
"""
from __future__ import annotations

import logging
import re
from datetime import UTC, datetime

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


db = Database()

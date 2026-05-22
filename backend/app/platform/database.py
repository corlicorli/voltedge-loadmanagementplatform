"""asyncpg connection pool + a minimal migration/seed runner.

A numeric->float codec is registered on every connection so NUMERIC columns
come back as plain Python floats, keeping the domain free of Decimal.
"""
from __future__ import annotations

import logging
from pathlib import Path

import asyncpg

from app.platform.config import settings

logger = logging.getLogger("voltedge.db")

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_MIGRATIONS_DIR = _BACKEND_ROOT / "migrations"
_SEEDS_DIR = _BACKEND_ROOT / "seeds"


async def _init_connection(conn: asyncpg.Connection) -> None:
    await conn.set_type_codec(
        "numeric", encoder=str, decoder=float, schema="pg_catalog", format="text"
    )


class Database:
    def __init__(self) -> None:
        self._pool: asyncpg.Pool | None = None

    @property
    def pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialised; call connect() first")
        return self._pool

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(
            dsn=settings.database_url, min_size=1, max_size=10, init=_init_connection
        )
        logger.info("database pool created")

    async def disconnect(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def run_migrations(self) -> None:
        """Apply every migrations/*.sql exactly once (tracked in schema_migrations)."""
        files = sorted(_MIGRATIONS_DIR.glob("*.sql"))
        async with self.pool.acquire() as conn:
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
            )
            for path in files:
                version = path.name
                applied = await conn.fetchval(
                    "SELECT 1 FROM schema_migrations WHERE version = $1", version
                )
                if applied:
                    continue
                async with conn.transaction():
                    await conn.execute(path.read_text())
                    await conn.execute(
                        "INSERT INTO schema_migrations (version) VALUES ($1)", version
                    )
                logger.info("applied migration %s", version)

    async def seed(self) -> None:
        """Run seeds/*.sql once, only when the database has no load areas yet."""
        async with self.pool.acquire() as conn:
            count = await conn.fetchval("SELECT count(*) FROM load_areas")
            if count and count > 0:
                logger.info("seed skipped: %s load area(s) already present", count)
                return
            for path in sorted(_SEEDS_DIR.glob("*.sql")):
                async with conn.transaction():
                    await conn.execute(path.read_text())
                logger.info("applied seed %s", path.name)


db = Database()

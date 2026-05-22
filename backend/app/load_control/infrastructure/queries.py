"""Read-side implementation (CQRS): serves queries from the warehouse views."""
from __future__ import annotations

from typing import Any

import asyncpg

from app.load_control.application.queries import LoadAreaQueries


class PostgresLoadAreaQueries(LoadAreaQueries):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def status(self, area_code: str) -> dict[str, Any] | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM v_load_area_status WHERE area_code = $1", area_code
            )
        return dict(row) if row else None

    async def active_sessions(self, area_code: str) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT session_id::text AS session_id, charger_id, requested_power_kw,
                       current_power_kw, status, started_at
                FROM v_active_sessions
                WHERE area_code = $1
                ORDER BY started_at
                """,
                area_code,
            )
        return [dict(r) for r in rows]

    async def adjustments(self, area_code: str, limit: int = 100) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT adjustment_id::text AS adjustment_id, session_id::text AS session_id,
                       previous_power_kw, new_power_kw, reason, created_at
                FROM v_load_adjustments
                WHERE area_code = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                area_code,
                limit,
            )
        return [dict(r) for r in rows]

    async def chargers(self, area_code: str) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT charger_id, area_code, max_power_kw, status
                FROM chargers
                WHERE area_code = $1
                ORDER BY charger_id
                """,
                area_code,
            )
        return [dict(r) for r in rows]

"""PostgreSQL implementation of the LoadAreaRepository port (asyncpg, raw SQL).

All SQL uses bound parameters ($1, $2, ...) — never string interpolation — so
the repository is safe against SQL injection.
"""
from __future__ import annotations

import uuid

import asyncpg

from app.load_control.domain.load_area import LoadArea
from app.load_control.domain.repository import LoadAreaNotFound, LoadAreaRepository
from app.load_control.domain.value_objects import AreaCode
from app.load_control.infrastructure.mappers import to_load_area


class PostgresLoadAreaRepository(LoadAreaRepository):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get(self, area_code: AreaCode) -> LoadArea:
        async with self._pool.acquire() as conn:
            area = await conn.fetchrow(
                "SELECT * FROM load_areas WHERE area_code = $1", area_code.value
            )
            if area is None:
                raise LoadAreaNotFound(area_code.value)
            chargers = await conn.fetch(
                "SELECT * FROM chargers WHERE area_code = $1 ORDER BY charger_id", area_code.value
            )
            sessions = await conn.fetch(
                "SELECT * FROM charging_sessions WHERE area_code = $1 AND status = 'ACTIVE'",
                area_code.value,
            )
            rules = await conn.fetch(
                "SELECT * FROM load_rules WHERE area_code = $1", area_code.value
            )
        return to_load_area(area, chargers, sessions, rules)

    async def save(self, area: LoadArea) -> None:
        async with self._pool.acquire() as conn, conn.transaction():
            await conn.execute(
                "UPDATE load_areas SET status = $2, updated_at = now() WHERE area_code = $1",
                area.area_code.value,
                area.status.value,
            )
            for charger in area.chargers:
                await conn.execute(
                    """
                    INSERT INTO chargers (charger_id, area_code, max_power_kw, status)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (charger_id) DO UPDATE
                        SET max_power_kw = EXCLUDED.max_power_kw, status = EXCLUDED.status
                    """,
                    charger.charger_id,
                    charger.area_code,
                    charger.max_power_kw,
                    charger.status.value,
                )
            for session in area.sessions:
                await conn.execute(
                    """
                    INSERT INTO charging_sessions
                        (session_id, area_code, charger_id, requested_power_kw,
                         current_power_kw, status, started_at, stopped_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (session_id) DO UPDATE
                        SET current_power_kw = EXCLUDED.current_power_kw,
                            status = EXCLUDED.status,
                            stopped_at = EXCLUDED.stopped_at
                    """,
                    uuid.UUID(session.session_id),
                    session.area_code,
                    session.charger_id,
                    session.requested_power.kw,
                    session.current_power.kw,
                    session.status.value,
                    session.started_at,
                    session.stopped_at,
                )
            for adj in area.adjustments:
                await conn.execute(
                    """
                    INSERT INTO load_adjustments
                        (adjustment_id, area_code, session_id, previous_power_kw,
                         new_power_kw, reason, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (adjustment_id) DO NOTHING
                    """,
                    uuid.UUID(adj.adjustment_id),
                    adj.area_code,
                    uuid.UUID(adj.session_id),
                    adj.previous_power_kw,
                    adj.new_power_kw,
                    adj.reason,
                    adj.created_at,
                )

    async def exists(self, area_code: AreaCode) -> bool:
        async with self._pool.acquire() as conn:
            found = await conn.fetchval(
                "SELECT 1 FROM load_areas WHERE area_code = $1", area_code.value
            )
        return found is not None

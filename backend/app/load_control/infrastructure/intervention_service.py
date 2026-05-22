"""Persists manual intervention requests (the ManualInterventionPolicy outcome)."""
from __future__ import annotations

import asyncpg

from app.load_control.application.ports import InterventionService


class PostgresInterventionService(InterventionService):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def open_request(
        self, area_code: str, reason: str, load_kw: float, max_capacity_kw: float
    ) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO intervention_requests
                    (request_id, area_code, reason, load_kw, max_capacity_kw, status)
                VALUES (gen_random_uuid(), $1, $2, $3, $4, 'OPEN')
                """,
                area_code,
                reason,
                load_kw,
                max_capacity_kw,
            )

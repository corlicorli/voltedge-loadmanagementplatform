"""AnalyticsService — descriptive and diagnostic analytics.

Reads the warehouse/read-model views built by the Load Control Context and
exposes the metrics consumed by the React BI dashboard (exam §6).
"""
from __future__ import annotations

import json
from typing import Any

import asyncpg


def _as_payload(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


class AnalyticsService:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    # ----- descriptive ------------------------------------------------------

    async def kpis(self, area_code: str) -> dict[str, Any] | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM v_area_kpis WHERE area_code = $1", area_code)
        return dict(row) if row else None

    async def load_timeseries(self, area_code: str, hours: int = 24) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT sampled_at, current_load_kw, available_capacity_kw,
                       status, active_session_count
                FROM v_load_timeseries
                WHERE area_code = $1 AND sampled_at >= now() - ($2 * interval '1 hour')
                ORDER BY sampled_at
                """,
                area_code,
                hours,
            )
        return [dict(r) for r in rows]

    async def hourly_utilisation(self, area_code: str, hours: int = 48) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT hour, avg_load_kw, peak_load_kw, avg_utilisation_pct,
                       peak_utilisation_pct, avg_sessions
                FROM v_load_utilisation_hourly
                WHERE area_code = $1 AND hour >= now() - ($2 * interval '1 hour')
                ORDER BY hour
                """,
                area_code,
                hours,
            )
        return [dict(r) for r in rows]

    async def daily_peaks(self, area_code: str, days: int = 7) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT day, peak_load_kw, avg_load_kw, peak_utilisation_pct,
                       critical_samples, warning_samples, stable_samples
                FROM v_peak_loads_daily
                WHERE area_code = $1 AND day >= now() - ($2 * interval '1 day')
                ORDER BY day
                """,
                area_code,
                days,
            )
        return [dict(r) for r in rows]

    async def status_distribution(self, area_code: str, days: int = 7) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT status, count(*) AS samples
                FROM load_samples
                WHERE area_code = $1 AND sampled_at >= now() - ($2 * interval '1 day')
                GROUP BY status
                """,
                area_code,
                days,
            )
        total = sum(r["samples"] for r in rows) or 1
        return [
            {"status": r["status"], "samples": r["samples"],
             "pct": round(r["samples"] * 100 / total, 2)}
            for r in rows
        ]

    # ----- diagnostic -------------------------------------------------------

    async def regulation_events(self, area_code: str, limit: int = 50) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT event_type, occurred_at, payload
                FROM v_regulation_events
                WHERE area_code = $1
                ORDER BY occurred_at DESC
                LIMIT $2
                """,
                area_code,
                limit,
            )
        return [
            {
                "event_type": r["event_type"],
                "occurred_at": r["occurred_at"],
                "payload": _as_payload(r["payload"]),
            }
            for r in rows
        ]

    async def event_counts(self, area_code: str, days: int = 7) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT event_type, day, event_count
                FROM v_event_daily_counts
                WHERE area_code = $1 AND day >= now() - ($2 * interval '1 day')
                ORDER BY day, event_type
                """,
                area_code,
                days,
            )
        return [dict(r) for r in rows]

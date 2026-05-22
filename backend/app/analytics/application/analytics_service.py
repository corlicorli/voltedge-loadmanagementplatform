"""AnalyticsService — descriptive, diagnostic and predictive analytics.

Reads the warehouse/read-model views built by the Load Control Context. The
predictive forecast is a transparent, data-driven baseline (hour-of-day
historical average), i.e. the extension point the report describes for future
load forecasting — not a black-box model.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import asyncpg


def _classify(load_kw: float, warning_kw: float, critical_kw: float) -> str:
    if load_kw >= critical_kw:
        return "CRITICAL"
    if load_kw >= warning_kw:
        return "WARNING"
    return "STABLE"


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

    # ----- predictive -------------------------------------------------------

    async def forecast(self, area_code: str, horizon_hours: int = 12) -> dict[str, Any] | None:
        async with self._pool.acquire() as conn:
            area = await conn.fetchrow(
                "SELECT max_capacity_kw, warning_fraction, critical_fraction "
                "FROM load_areas WHERE area_code = $1",
                area_code,
            )
            if area is None:
                return None
            profile_rows = await conn.fetch(
                """
                SELECT extract(hour FROM sampled_at)::int AS hod, avg(current_load_kw) AS avg_load
                FROM load_samples
                WHERE area_code = $1
                GROUP BY hod
                """,
                area_code,
            )

        profile = {r["hod"]: r["avg_load"] for r in profile_rows}
        overall = sum(profile.values()) / len(profile) if profile else 0.0
        max_kw = area["max_capacity_kw"]
        warning_kw = max_kw * area["warning_fraction"]
        critical_kw = max_kw * area["critical_fraction"]

        now = datetime.now(UTC)
        points = []
        for hour in range(1, horizon_hours + 1):
            moment = now + timedelta(hours=hour)
            predicted = round(profile.get(moment.hour, overall), 3)
            points.append(
                {
                    "timestamp": moment,
                    "predicted_load_kw": predicted,
                    "predicted_utilisation_pct": round(predicted / max_kw * 100, 2),
                    "predicted_status": _classify(predicted, warning_kw, critical_kw),
                }
            )
        return {
            "area_code": area_code,
            "method": "hour-of-day historical average",
            "max_capacity_kw": max_kw,
            "horizon_hours": horizon_hours,
            "points": points,
        }

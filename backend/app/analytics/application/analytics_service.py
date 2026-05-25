"""AnalyticsService — descriptive and diagnostic analytics.

Computes the metrics consumed by the React BI dashboard (exam §6) with MongoDB
aggregation pipelines — the document-database equivalents of the SQL warehouse
views built by the Load Control Context. Read-only: analytics never writes.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from app.platform.database import Database, utcnow

# Diagnostic: the regulation-related events surfaced from the event store.
_REGULATION_EVENTS = [
    "LoadThresholdReached",
    "LoadRuleActivated",
    "RegulationResultEvaluated",
    "LoadAreaStabilized",
    "RegulationFailed",
]


class AnalyticsService:
    def __init__(self, db: Database) -> None:
        self._db = db

    # ----- descriptive ------------------------------------------------------

    async def kpis(self, area_code: str) -> dict[str, Any] | None:
        area = await self._db.load_areas.find_one({"_id": area_code})
        if area is None:
            return None
        max_cap = area["max_capacity_kw"]
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

        peak = await self._db.load_samples.aggregate(
            [
                {
                    "$match": {
                        "area_code": area_code,
                        "sampled_at": {"$gte": utcnow() - timedelta(hours=24)},
                    }
                },
                {"$group": {"_id": None, "peak": {"$max": "$current_load_kw"}}},
            ]
        ).to_list(length=1)
        peak_24h = round(peak[0]["peak"], 3) if peak and peak[0]["peak"] is not None else None

        total_adjustments = await self._db.load_adjustments.count_documents(
            {"area_code": area_code}
        )
        open_interventions = await self._db.intervention_requests.count_documents(
            {"area_code": area_code, "status": "OPEN"}
        )
        return {
            "area_code": area["_id"],
            "area_name": area["area_name"],
            "current_load_kw": round(current_load, 3),
            "max_capacity_kw": max_cap,
            "available_capacity_kw": round(max_cap - current_load, 3),
            "status": area["status"],
            "active_session_count": active_count,
            "current_utilisation_pct": round(current_load / max_cap * 100, 2),
            "peak_load_24h_kw": peak_24h,
            "total_adjustments": total_adjustments,
            "open_interventions": open_interventions,
        }

    async def load_timeseries(self, area_code: str, hours: int = 24) -> list[dict[str, Any]]:
        since = utcnow() - timedelta(hours=hours)
        docs = (
            await self._db.load_samples.find(
                {"area_code": area_code, "sampled_at": {"$gte": since}}
            )
            .sort("sampled_at", 1)
            .to_list(length=None)
        )
        return [
            {
                "sampled_at": d["sampled_at"],
                "current_load_kw": d["current_load_kw"],
                "available_capacity_kw": d["available_capacity_kw"],
                "status": d["status"],
                "active_session_count": d["active_session_count"],
            }
            for d in docs
        ]

    async def hourly_utilisation(self, area_code: str, hours: int = 48) -> list[dict[str, Any]]:
        max_cap = await self._max_capacity(area_code)
        if max_cap is None:
            return []
        since = utcnow() - timedelta(hours=hours)
        rows = await self._db.load_samples.aggregate(
            [
                {"$match": {"area_code": area_code, "sampled_at": {"$gte": since}}},
                {
                    "$group": {
                        "_id": {"$dateTrunc": {"date": "$sampled_at", "unit": "hour"}},
                        "avg_load_kw": {"$avg": "$current_load_kw"},
                        "peak_load_kw": {"$max": "$current_load_kw"},
                        "avg_sessions": {"$avg": "$active_session_count"},
                    }
                },
                {"$sort": {"_id": 1}},
            ]
        ).to_list(length=None)
        return [
            {
                "hour": r["_id"],
                "avg_load_kw": round(r["avg_load_kw"], 3),
                "peak_load_kw": round(r["peak_load_kw"], 3),
                "avg_utilisation_pct": round(r["avg_load_kw"] / max_cap * 100, 2),
                "peak_utilisation_pct": round(r["peak_load_kw"] / max_cap * 100, 2),
                "avg_sessions": round(r["avg_sessions"], 1),
            }
            for r in rows
        ]

    async def daily_peaks(self, area_code: str, days: int = 7) -> list[dict[str, Any]]:
        max_cap = await self._max_capacity(area_code)
        if max_cap is None:
            return []
        since = utcnow() - timedelta(days=days)
        rows = await self._db.load_samples.aggregate(
            [
                {"$match": {"area_code": area_code, "sampled_at": {"$gte": since}}},
                {
                    "$group": {
                        "_id": {"$dateTrunc": {"date": "$sampled_at", "unit": "day"}},
                        "peak_load_kw": {"$max": "$current_load_kw"},
                        "avg_load_kw": {"$avg": "$current_load_kw"},
                        "critical_samples": {
                            "$sum": {"$cond": [{"$eq": ["$status", "CRITICAL"]}, 1, 0]}
                        },
                        "warning_samples": {
                            "$sum": {"$cond": [{"$eq": ["$status", "WARNING"]}, 1, 0]}
                        },
                        "stable_samples": {
                            "$sum": {"$cond": [{"$eq": ["$status", "STABLE"]}, 1, 0]}
                        },
                    }
                },
                {"$sort": {"_id": 1}},
            ]
        ).to_list(length=None)
        return [
            {
                "day": r["_id"],
                "peak_load_kw": round(r["peak_load_kw"], 3),
                "avg_load_kw": round(r["avg_load_kw"], 3),
                "peak_utilisation_pct": round(r["peak_load_kw"] / max_cap * 100, 2),
                "critical_samples": r["critical_samples"],
                "warning_samples": r["warning_samples"],
                "stable_samples": r["stable_samples"],
            }
            for r in rows
        ]

    async def status_distribution(self, area_code: str, days: int = 7) -> list[dict[str, Any]]:
        since = utcnow() - timedelta(days=days)
        rows = await self._db.load_samples.aggregate(
            [
                {"$match": {"area_code": area_code, "sampled_at": {"$gte": since}}},
                {"$group": {"_id": "$status", "samples": {"$sum": 1}}},
            ]
        ).to_list(length=None)
        total = sum(r["samples"] for r in rows) or 1
        return [
            {
                "status": r["_id"],
                "samples": r["samples"],
                "pct": round(r["samples"] * 100 / total, 2),
            }
            for r in rows
        ]

    # ----- diagnostic -------------------------------------------------------

    async def regulation_events(self, area_code: str, limit: int = 50) -> list[dict[str, Any]]:
        docs = (
            await self._db.domain_events.find(
                {"aggregate_id": area_code, "event_type": {"$in": _REGULATION_EVENTS}}
            )
            .sort("occurred_at", -1)
            .limit(limit)
            .to_list(length=None)
        )
        return [
            {
                "event_type": d["event_type"],
                "occurred_at": d["occurred_at"],
                "payload": d["payload"],
            }
            for d in docs
        ]

    async def event_counts(self, area_code: str, days: int = 7) -> list[dict[str, Any]]:
        since = utcnow() - timedelta(days=days)
        rows = await self._db.domain_events.aggregate(
            [
                {"$match": {"aggregate_id": area_code, "occurred_at": {"$gte": since}}},
                {
                    "$group": {
                        "_id": {
                            "event_type": "$event_type",
                            "day": {"$dateTrunc": {"date": "$occurred_at", "unit": "day"}},
                        },
                        "event_count": {"$sum": 1},
                    }
                },
                {"$sort": {"_id.day": 1, "_id.event_type": 1}},
            ]
        ).to_list(length=None)
        return [
            {
                "event_type": r["_id"]["event_type"],
                "day": r["_id"]["day"],
                "event_count": r["event_count"],
            }
            for r in rows
        ]

    # ----- helpers ----------------------------------------------------------

    async def _max_capacity(self, area_code: str) -> float | None:
        area = await self._db.load_areas.find_one({"_id": area_code}, {"max_capacity_kw": 1})
        return area["max_capacity_kw"] if area else None

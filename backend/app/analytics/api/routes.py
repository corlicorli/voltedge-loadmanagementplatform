"""Analytics REST API consumed by the React BI dashboard."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.analytics.api.schemas import (
    DailyPeak,
    EventCount,
    ForecastResponse,
    HourlyUtilisation,
    KpiResponse,
    LoadSamplePoint,
    RegulationEvent,
    StatusDistribution,
)
from app.analytics.application.analytics_service import AnalyticsService
from app.platform.database import db

router = APIRouter(prefix="/analytics", tags=["analytics"])


def get_analytics() -> AnalyticsService:
    return AnalyticsService(db.pool)


@router.get("/{area_code}/kpis", response_model=KpiResponse, summary="Headline KPIs")
async def kpis(area_code: str, svc: AnalyticsService = Depends(get_analytics)) -> KpiResponse:
    row = await svc.kpis(area_code)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Load area '{area_code}' not found")
    return KpiResponse.model_validate(row)


@router.get(
    "/{area_code}/load-timeseries",
    response_model=list[LoadSamplePoint],
    summary="Descriptive: load over time",
)
async def load_timeseries(
    area_code: str,
    hours: int = Query(24, ge=1, le=720),
    svc: AnalyticsService = Depends(get_analytics),
) -> list[LoadSamplePoint]:
    return [LoadSamplePoint.model_validate(r) for r in await svc.load_timeseries(area_code, hours)]


@router.get(
    "/{area_code}/hourly-utilisation",
    response_model=list[HourlyUtilisation],
    summary="Descriptive: hourly utilisation",
)
async def hourly_utilisation(
    area_code: str,
    hours: int = Query(48, ge=1, le=720),
    svc: AnalyticsService = Depends(get_analytics),
) -> list[HourlyUtilisation]:
    return [
        HourlyUtilisation.model_validate(r) for r in await svc.hourly_utilisation(area_code, hours)
    ]


@router.get(
    "/{area_code}/daily-peaks",
    response_model=list[DailyPeak],
    summary="Descriptive: daily peak loads",
)
async def daily_peaks(
    area_code: str,
    days: int = Query(7, ge=1, le=90),
    svc: AnalyticsService = Depends(get_analytics),
) -> list[DailyPeak]:
    return [DailyPeak.model_validate(r) for r in await svc.daily_peaks(area_code, days)]


@router.get(
    "/{area_code}/status-distribution",
    response_model=list[StatusDistribution],
    summary="Descriptive: time spent in each status",
)
async def status_distribution(
    area_code: str,
    days: int = Query(7, ge=1, le=90),
    svc: AnalyticsService = Depends(get_analytics),
) -> list[StatusDistribution]:
    return [
        StatusDistribution.model_validate(r) for r in await svc.status_distribution(area_code, days)
    ]


@router.get(
    "/{area_code}/regulation-events",
    response_model=list[RegulationEvent],
    summary="Diagnostic: why regulation happened",
)
async def regulation_events(
    area_code: str,
    limit: int = Query(50, ge=1, le=500),
    svc: AnalyticsService = Depends(get_analytics),
) -> list[RegulationEvent]:
    rows = await svc.regulation_events(area_code, limit)
    return [RegulationEvent.model_validate(r) for r in rows]


@router.get(
    "/{area_code}/event-counts",
    response_model=list[EventCount],
    summary="Diagnostic: domain event counts per day",
)
async def event_counts(
    area_code: str,
    days: int = Query(7, ge=1, le=90),
    svc: AnalyticsService = Depends(get_analytics),
) -> list[EventCount]:
    return [EventCount.model_validate(r) for r in await svc.event_counts(area_code, days)]


@router.get(
    "/{area_code}/forecast",
    response_model=ForecastResponse,
    summary="Predictive: hour-of-day load forecast",
)
async def forecast(
    area_code: str,
    horizon_hours: int = Query(12, ge=1, le=48),
    svc: AnalyticsService = Depends(get_analytics),
) -> ForecastResponse:
    result = await svc.forecast(area_code, horizon_hours)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Load area '{area_code}' not found")
    return ForecastResponse.model_validate(result)

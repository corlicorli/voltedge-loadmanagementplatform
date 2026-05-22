"""REST API for the Load Control Context."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.load_control.api.schemas import (
    AdjustmentResponse,
    AreaStatusResponse,
    ChargerResponse,
    RegisterChargerRequest,
    SessionResponse,
    StartSessionRequest,
    StartSessionResponse,
)
from app.load_control.application.commands import (
    EvaluateLoadAreaCapacity,
    RegisterCharger,
    StartChargingSession,
)
from app.load_control.application.load_control_service import LoadControlService
from app.load_control.infrastructure.queries import PostgresLoadAreaQueries
from app.platform.dependencies import get_queries, get_service

router = APIRouter(prefix="/load-areas", tags=["load-control"])


async def _require_status(queries: PostgresLoadAreaQueries, area_code: str) -> dict:
    row = await queries.status(area_code)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Load area '{area_code}' not found")
    return row


@router.post(
    "/{area_code}/sessions",
    response_model=StartSessionResponse,
    status_code=201,
    summary="Start a new charging session in a load area",
)
async def start_session(
    area_code: str,
    body: StartSessionRequest,
    service: LoadControlService = Depends(get_service),
    queries: PostgresLoadAreaQueries = Depends(get_queries),
) -> StartSessionResponse:
    session_id = await service.start_charging_session(
        StartChargingSession(
            area_code=area_code, charger_id=body.charger_id, power_kw=body.power_level_kw
        )
    )
    status_row = await _require_status(queries, area_code)
    return StartSessionResponse(
        session_id=session_id, area_status=AreaStatusResponse.model_validate(status_row)
    )


@router.get(
    "/{area_code}/status",
    response_model=AreaStatusResponse,
    summary="Get current LoadStatus and currentLoad",
)
async def get_status(
    area_code: str, queries: PostgresLoadAreaQueries = Depends(get_queries)
) -> AreaStatusResponse:
    return AreaStatusResponse.model_validate(await _require_status(queries, area_code))


@router.get(
    "/{area_code}/sessions",
    response_model=list[SessionResponse],
    summary="Get active charging sessions",
)
async def list_sessions(
    area_code: str, queries: PostgresLoadAreaQueries = Depends(get_queries)
) -> list[SessionResponse]:
    await _require_status(queries, area_code)
    rows = await queries.active_sessions(area_code)
    return [SessionResponse.model_validate(r) for r in rows]


@router.get(
    "/{area_code}/adjustments",
    response_model=list[AdjustmentResponse],
    summary="Get load adjustments made by regulation",
)
async def list_adjustments(
    area_code: str,
    limit: int = Query(100, ge=1, le=1000),
    queries: PostgresLoadAreaQueries = Depends(get_queries),
) -> list[AdjustmentResponse]:
    await _require_status(queries, area_code)
    rows = await queries.adjustments(area_code, limit)
    return [AdjustmentResponse.model_validate(r) for r in rows]


@router.post(
    "/{area_code}/evaluate",
    response_model=AreaStatusResponse,
    summary="Evaluate load and activate regulation if needed",
)
async def evaluate(
    area_code: str,
    service: LoadControlService = Depends(get_service),
    queries: PostgresLoadAreaQueries = Depends(get_queries),
) -> AreaStatusResponse:
    await service.evaluate_capacity(EvaluateLoadAreaCapacity(area_code=area_code))
    return AreaStatusResponse.model_validate(await _require_status(queries, area_code))


@router.post(
    "/{area_code}/chargers",
    response_model=ChargerResponse,
    status_code=201,
    summary="Register a new charger in a load area",
)
async def register_charger(
    area_code: str,
    body: RegisterChargerRequest,
    service: LoadControlService = Depends(get_service),
) -> ChargerResponse:
    charger = await service.register_charger(
        RegisterCharger(
            area_code=area_code, charger_id=body.charger_id, max_power_kw=body.max_power_kw
        )
    )
    return ChargerResponse.model_validate(charger)


@router.get(
    "/{area_code}/chargers",
    response_model=list[ChargerResponse],
    summary="List chargers in a load area",
)
async def list_chargers(
    area_code: str, queries: PostgresLoadAreaQueries = Depends(get_queries)
) -> list[ChargerResponse]:
    await _require_status(queries, area_code)
    rows = await queries.chargers(area_code)
    return [ChargerResponse.model_validate(r) for r in rows]

"""REST API for the Load Control Context."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.load_control.api.schemas import (
    AdjustmentResponse,
    AreaStatusResponse,
    AreaSummary,
    ChargerResponse,
    CreateLoadAreaRequest,
    RegisterChargerRequest,
    SessionResponse,
    StartSessionRequest,
    StartSessionResponse,
)
from app.load_control.application.commands import (
    CreateLoadArea,
    EvaluateLoadAreaCapacity,
    RecordChargerHeartbeat,
    RegisterCharger,
    StartChargingSession,
)
from app.load_control.application.load_control_service import LoadControlService
from app.load_control.infrastructure.queries import MongoLoadAreaQueries
from app.platform.dependencies import get_queries, get_service

router = APIRouter(prefix="/load-areas", tags=["load-control"])


async def _require_status(queries: MongoLoadAreaQueries, area_code: str) -> dict:
    row = await queries.status(area_code)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Load area '{area_code}' not found")
    return row


@router.post(
    "",
    response_model=AreaStatusResponse,
    status_code=201,
    summary="Register a new load area (onboarding)",
)
async def create_load_area(
    body: CreateLoadAreaRequest,
    service: LoadControlService = Depends(get_service),
    queries: MongoLoadAreaQueries = Depends(get_queries),
) -> AreaStatusResponse:
    area_code = await service.create_load_area(
        CreateLoadArea(
            area_code=body.area_code,
            area_name=body.area_name,
            max_capacity_kw=body.max_capacity_kw,
            warning_fraction=body.warning_fraction,
            critical_fraction=body.critical_fraction,
            reduction_fraction=body.reduction_fraction,
        )
    )
    return AreaStatusResponse.model_validate(await _require_status(queries, area_code))


@router.get("", response_model=list[AreaSummary], summary="List all registered load areas")
async def list_areas(queries: MongoLoadAreaQueries = Depends(get_queries)) -> list[AreaSummary]:
    return [AreaSummary.model_validate(r) for r in await queries.list_areas()]


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
    queries: MongoLoadAreaQueries = Depends(get_queries),
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
    area_code: str, queries: MongoLoadAreaQueries = Depends(get_queries)
) -> AreaStatusResponse:
    return AreaStatusResponse.model_validate(await _require_status(queries, area_code))


@router.get(
    "/{area_code}/sessions",
    response_model=list[SessionResponse],
    summary="Get active charging sessions",
)
async def list_sessions(
    area_code: str, queries: MongoLoadAreaQueries = Depends(get_queries)
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
    queries: MongoLoadAreaQueries = Depends(get_queries),
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
    queries: MongoLoadAreaQueries = Depends(get_queries),
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
            area_code=area_code,
            charger_id=body.charger_id,
            max_power_kw=body.max_power_kw,
            name=body.name,
        )
    )
    return ChargerResponse.model_validate(charger)


@router.get(
    "/{area_code}/chargers",
    response_model=list[ChargerResponse],
    summary="List chargers in a load area",
)
async def list_chargers(
    area_code: str, queries: MongoLoadAreaQueries = Depends(get_queries)
) -> list[ChargerResponse]:
    await _require_status(queries, area_code)
    rows = await queries.chargers(area_code)
    return [ChargerResponse.model_validate(r) for r in rows]


@router.get(
    "/{area_code}/chargers/{charger_id}",
    response_model=ChargerResponse,
    summary="Get one charger: name, occupancy, online/offline, current output",
)
async def get_charger(
    area_code: str, charger_id: str, queries: MongoLoadAreaQueries = Depends(get_queries)
) -> ChargerResponse:
    row = await queries.charger(area_code, charger_id)
    if row is None:
        raise HTTPException(
            status_code=404, detail=f"Charger '{charger_id}' not found in area '{area_code}'"
        )
    return ChargerResponse.model_validate(row)


@router.post(
    "/{area_code}/chargers/{charger_id}/heartbeat",
    response_model=ChargerResponse,
    summary="Charger heartbeat — marks it online (refreshes last seen)",
)
async def charger_heartbeat(
    area_code: str,
    charger_id: str,
    service: LoadControlService = Depends(get_service),
    queries: MongoLoadAreaQueries = Depends(get_queries),
) -> ChargerResponse:
    await service.record_charger_heartbeat(
        RecordChargerHeartbeat(area_code=area_code, charger_id=charger_id)
    )
    row = await queries.charger(area_code, charger_id)
    if row is None:
        raise HTTPException(
            status_code=404, detail=f"Charger '{charger_id}' not found in area '{area_code}'"
        )
    return ChargerResponse.model_validate(row)

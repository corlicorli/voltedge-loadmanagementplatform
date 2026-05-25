"""VoltEdge Load Control Service — FastAPI application entrypoint."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.analytics.api.routes import router as analytics_router
from app.load_control.api.routes import router as load_control_router
from app.load_control.domain.repository import LoadAreaNotFound
from app.platform.config import settings
from app.platform.database import db
from app.platform.logging_config import configure_logging

logger = logging.getLogger("voltedge.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_level)
    await db.connect()
    if not await db.ping():
        raise RuntimeError("MongoDB is not reachable; check MONGO_URL")
    await db.init_indexes()
    if settings.seed_on_startup:
        await db.seed()
    logger.info("Load Control Service started (env=%s)", settings.app_env)
    yield
    await db.disconnect()


def create_app() -> FastAPI:
    app = FastAPI(
        title="VoltEdge Load Control Service",
        description=(
            "Load Management MVP — the Load Control Context, built with "
            "Domain-Driven Design (API / Application / Domain / Infrastructure)."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS so the React BI dashboard (separate origin) can call the API.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(LoadAreaNotFound)
    async def _not_found_handler(request, exc: LoadAreaNotFound):
        return JSONResponse(
            status_code=404,
            content={"error": "load_area_not_found", "detail": str(exc)},
        )

    @app.exception_handler(ValueError)
    async def _validation_handler(request, exc: ValueError):
        # Domain invariant violations (e.g. power exceeds charger max).
        return JSONResponse(
            status_code=422,
            content={"error": "domain_validation_error", "detail": str(exc)},
        )

    app.include_router(load_control_router)
    app.include_router(analytics_router)

    @app.get("/health", tags=["ops"], summary="Liveness + database readiness")
    async def health():
        if not await db.ping():
            raise HTTPException(status_code=503, detail="database unavailable")
        return {"status": "ok", "database": "up", "service": "load-control"}

    @app.get("/", tags=["ops"], summary="Service info")
    async def root():
        return {
            "service": "VoltEdge Load Control Service",
            "context": "Load Control Context",
            "docs": "/docs",
            "health": "/health",
            "metrics": "/metrics",
        }

    # Operational metrics for Prometheus/Grafana (exam §5, separate from BI).
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    return app


app = create_app()

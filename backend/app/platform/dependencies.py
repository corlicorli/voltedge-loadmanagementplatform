"""FastAPI dependency providers — wire infrastructure adapters to the shared pool."""
from __future__ import annotations

from app.load_control.application.load_control_service import LoadControlService
from app.load_control.infrastructure.event_publisher import PostgresEventPublisher
from app.load_control.infrastructure.intervention_service import PostgresInterventionService
from app.load_control.infrastructure.queries import PostgresLoadAreaQueries
from app.load_control.infrastructure.repository import PostgresLoadAreaRepository
from app.platform.database import db


def get_service() -> LoadControlService:
    pool = db.pool
    return LoadControlService(
        areas=PostgresLoadAreaRepository(pool),
        events=PostgresEventPublisher(pool),
        interventions=PostgresInterventionService(pool),
    )


def get_queries() -> PostgresLoadAreaQueries:
    return PostgresLoadAreaQueries(db.pool)

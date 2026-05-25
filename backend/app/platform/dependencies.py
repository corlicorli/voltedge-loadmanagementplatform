"""FastAPI dependency providers — wire infrastructure adapters to the Mongo db."""
from __future__ import annotations

from app.load_control.application.load_control_service import LoadControlService
from app.load_control.infrastructure.event_publisher import MongoEventPublisher
from app.load_control.infrastructure.intervention_service import MongoInterventionService
from app.load_control.infrastructure.queries import MongoLoadAreaQueries
from app.load_control.infrastructure.repository import MongoLoadAreaRepository
from app.platform.database import db


def get_service() -> LoadControlService:
    return LoadControlService(
        areas=MongoLoadAreaRepository(db),
        events=MongoEventPublisher(db),
        interventions=MongoInterventionService(db),
    )


def get_queries() -> MongoLoadAreaQueries:
    return MongoLoadAreaQueries(db)

"""Shared pytest fixtures.

Unit tests need nothing. API/integration tests need a MongoDB reachable at
MONGO_URL; if none is reachable they are skipped (so `pytest` still runs the
unit suite anywhere). The test database (MONGO_DB) is dropped and re-seeded at
the start of the session so the suite is deterministic and never touches the
development database.
"""
from __future__ import annotations

import os
import socket
from urllib.parse import urlsplit

import pytest

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("MONGO_DB", "voltedge_test")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("SEED_ON_STARTUP", "true")


def _db_reachable() -> bool:
    parts = urlsplit(os.environ["MONGO_URL"])
    host = parts.hostname or "localhost"
    port = parts.port or 27017
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def _build_baseline(client) -> None:
    """Build the YN demo baseline via the API (the system ships empty — no seed).

    Mirrors the Postman "Onboarding" folder: register YN + its 24 chargers + 22
    baseline sessions (21x11 + 1x2 = 233 kW), leaving YN-23/YN-24 free for the tests.
    """
    client.post(
        "/load-areas",
        json={"areaCode": "YN", "areaName": "Ydre Nørrebro", "maxCapacityKw": 240},
    )
    for g in range(1, 25):
        client.post("/load-areas/YN/chargers", json={"chargerId": f"YN-{g:02d}", "maxPowerKw": 11})
    for g in range(1, 22):
        client.post("/load-areas/YN/sessions", json={"chargerId": f"YN-{g:02d}", "powerLevelKw": 11})
    client.post("/load-areas/YN/sessions", json={"chargerId": "YN-22", "powerLevelKw": 2})


@pytest.fixture(scope="session")
def api_client():
    if not _db_reachable():
        pytest.skip("MongoDB not reachable at MONGO_URL; skipping API/integration tests")

    from pymongo import MongoClient

    # Start from a clean test database (never the dev DB); the baseline is built
    # through the API below, exactly as a real customer / the populator would.
    cleaner: MongoClient = MongoClient(os.environ["MONGO_URL"])
    cleaner.drop_database(os.environ["MONGO_DB"])
    cleaner.close()

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        _build_baseline(client)
        yield client

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


@pytest.fixture(scope="session")
def api_client():
    if not _db_reachable():
        pytest.skip("MongoDB not reachable at MONGO_URL; skipping API/integration tests")

    from pymongo import MongoClient

    # Start from a clean, freshly seeded test database (never the dev DB).
    cleaner: MongoClient = MongoClient(os.environ["MONGO_URL"])
    cleaner.drop_database(os.environ["MONGO_DB"])
    cleaner.close()

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        yield client

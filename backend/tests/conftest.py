"""Shared pytest fixtures.

Unit tests need nothing. API/integration tests need a PostgreSQL reachable at
DATABASE_URL; if none is reachable they are skipped (so `pytest` still runs the
unit suite anywhere).
"""
from __future__ import annotations

import os
import re
import socket

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://voltedge:voltedge@localhost:5432/voltedge")
os.environ.setdefault("LOG_LEVEL", "WARNING")


def _db_reachable() -> bool:
    match = re.search(r"@([^:/]+):(\d+)", os.environ["DATABASE_URL"])
    host, port = (match.group(1), int(match.group(2))) if match else ("localhost", 5432)
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


@pytest.fixture(scope="session")
def api_client():
    if not _db_reachable():
        pytest.skip("PostgreSQL not reachable at DATABASE_URL; skipping API/integration tests")
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        yield client

"""Shared fixtures: isolated SQLite DB + TestClient, one registered user."""

from __future__ import annotations

import os
import tempfile

# bind the test database before any app module is imported (the engine
# reads SPIIK_DB once at import time)
_TEST_DIR = tempfile.mkdtemp(prefix="spiik-test-")
os.environ["SPIIK_DB"] = os.path.join(_TEST_DIR, "spiik-test.db")
os.environ["SPIIK_SECRET"] = "test-secret"

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    from app.db import Base, engine
    from app.main import app

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth(client):
    """Auth headers for a freshly registered user 'ana'."""
    res = client.post(
        "/api/auth/register",
        json={"username": "ana", "email": "ana@example.com", "password": "s3cretpass"},
    )
    assert res.status_code == 201, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}

"""
tests/conftest.py — Shared fixtures for Phase 3 tests.

Uses an in-memory SQLite engine (StaticPool, so all connections share the
same DB) instead of a real Postgres server, so tests run without external
infrastructure. We patch app.core.db.engine and app.api.depedencies.engine
so both the FastAPI lifespan's init_db() and per-request sessions use it.
"""
import pytest
from unittest.mock import patch
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

import sys
from pathlib import Path
# Add the project root to Python path so 'app' can be imported
# This works regardless of where pytest is run from
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


@pytest.fixture(name="db_engine")
def db_engine_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from app import models  # noqa: F401  (ensure all tables are registered)
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture(db_engine):
    with patch("app.core.db.engine", db_engine):
        from app.main import create_app
        from app.api.depedencies import get_db

        app = create_app()

        def get_db_override():
            with Session(db_engine) as session:
                yield session

        app.dependency_overrides[get_db] = get_db_override

        with TestClient(app) as c:
            yield c

        app.dependency_overrides.clear()


@pytest.fixture(name="superuser_token_headers")
def superuser_token_headers_fixture(client):
    """Log in as the bootstrapped FIRST_SUPERUSER and return auth headers."""
    from app.core.config import get_settings
    settings = get_settings()
    resp = client.post(
        "/login/access-token",
        data={
            "username": settings.FIRST_SUPERUSER,
            "password": settings.FIRST_SUPERUSER_PASSWORD,
        },
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(name="normal_user_token_headers")
def normal_user_token_headers_fixture(client):
    """Sign up a regular (non-superuser) test user and return auth headers."""
    email = "regular.user@example.com"
    password = "regularpass123"
    client.post(
        "/users/signup",
        json={"email": email, "password": password, "full_name": "Regular User"},
    )
    resp = client.post(
        "/login/access-token",
        data={"username": email, "password": password},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

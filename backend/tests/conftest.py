"""Shared test fixtures.

Unit tests never touch a database. Integration tests use a real Postgres (and Redis, for
rate-limit storage) rather than mocks - they read DATABASE_URL / REDIS_URL and skip
automatically if the corresponding service isn't reachable, so `pytest` still runs clean on a
laptop with nothing running, while CI (which starts real service containers) runs everything.
"""

import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://orbit:orbit@localhost:5432/orbit_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-do-not-use-in-production")
os.environ.setdefault("STRIPE_MOCK", "true")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_mock_test_secret")

import pytest


@pytest.fixture(scope="session")
def database_url() -> str:
    return os.environ["DATABASE_URL"]


@pytest.fixture(scope="session")
def db_engine(database_url: str):
    from sqlalchemy import create_engine, text

    engine = create_engine(database_url)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        pytest.skip(f"No reachable Postgres at {database_url}; skipping integration tests.")

    from alembic import command
    from alembic.config import Config

    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    alembic_cfg = Config(os.path.join(backend_dir, "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_cfg, "head")

    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker

    session_factory = sessionmaker(bind=db_engine, future=True)
    session = session_factory()
    yield session
    session.rollback()
    for table in ("refresh_tokens", "usage_events", "subscriptions", "workspace_members", "workspaces", "users"):
        session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
    session.commit()
    session.close()


@pytest.fixture(scope="session")
def redis_url() -> str:
    return os.environ["REDIS_URL"]


@pytest.fixture
def redis_client(redis_url: str):
    import redis as redis_sync

    try:
        client = redis_sync.from_url(redis_url, decode_responses=True)
        client.ping()
    except Exception:
        pytest.skip(f"No reachable Redis at {redis_url}; skipping.")

    yield client
    client.flushdb()
    client.close()


@pytest.fixture(autouse=True)
def _reset_stripe_client():
    """MockStripeClient is a process-wide singleton (see stripe_client.get_stripe_client's
    lru_cache - required so a subscription created in one request can be retrieved/modified in
    a later one). Clear it between tests so no in-memory Stripe state leaks across tests."""
    from app.integrations.stripe_client import get_stripe_client

    get_stripe_client.cache_clear()
    yield
    get_stripe_client.cache_clear()


@pytest.fixture
def client(db_session, redis_client):
    from fastapi.testclient import TestClient

    from app.core.db import get_db
    from app.main import app

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()

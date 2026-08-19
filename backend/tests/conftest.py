from __future__ import annotations

import os

# Configure the environment BEFORE importing the application.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://nvidia:nvidia@127.0.0.1:5432/nvidia_ai_test"
)
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("NVIDIA_API_KEY", "test-key")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("COOKIE_SECURE", "false")
os.environ.setdefault("MAX_REQUESTS_PER_MINUTE", "1000")
os.environ.setdefault("AUTH_MAX_ATTEMPTS_PER_MINUTE", "1000")
os.environ.setdefault("UPLOAD_DIR", "/tmp/nvai-test-uploads")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import MaintenanceState, ModelConfig  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app import ratelimit  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.add(ModelConfig(
            id="meta/llama-3.1-8b-instruct", display_name="Llama 3.1 8B",
            description="test", capabilities=["chat"], context_window=128000,
            supports_vision=False, enabled=True, sort_order=10,
        ))
        db.add(ModelConfig(
            id="disabled/model", display_name="Disabled", description="",
            capabilities=[], context_window=1000, supports_vision=False,
            enabled=False, sort_order=99,
        ))
        db.add(MaintenanceState(id=1, maintenance_mode=False))
        # Seed an initial admin so API-registered test users are never "first"
        # (the first registered user is auto-promoted to admin).
        from app.models import User, UserSettings
        from app.security import hash_password

        admin = User(email="seed-admin@example.com", password_hash=hash_password("seedadmin123"),
                     role="admin")
        db.add(admin)
        db.flush()
        db.add(UserSettings(user_id=admin.id))
        db.commit()
    finally:
        db.close()
    yield


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    ratelimit.reset()
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _csrf_headers(client: TestClient) -> dict:
    token = client.cookies.get(settings.csrf_cookie_name)
    return {"X-CSRF-Token": token} if token else {}


@pytest.fixture
def auth_client(client):
    """A registered + logged-in client, plus a helper to build CSRF headers."""
    import uuid as _uuid

    email = f"user_{_uuid.uuid4().hex[:8]}@example.com"
    resp = client.post("/api/auth/register", json={"email": email, "password": "supersecret1"})
    assert resp.status_code == 201, resp.text

    def csrf():
        return _csrf_headers(client)

    client.csrf = csrf  # type: ignore[attr-defined]
    client.email = email  # type: ignore[attr-defined]
    return client

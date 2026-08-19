from __future__ import annotations

import uuid


def test_register_login_logout(client):
    email = f"a_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/api/auth/register", json={"email": email, "password": "supersecret1"})
    assert r.status_code == 201
    assert r.json()["email"] == email
    # Session cookie is HTTP-only; CSRF cookie is present for the SPA.
    assert client.cookies.get("nvai_session") is not None

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == email

    csrf = {"X-CSRF-Token": client.cookies.get("nvai_csrf")}
    out = client.post("/api/auth/logout", headers=csrf)
    assert out.status_code == 204

    # After logout the session is revoked.
    assert client.get("/api/auth/me").status_code == 401


def test_login_wrong_password(client):
    email = f"b_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/auth/register", json={"email": email, "password": "supersecret1"})
    client.cookies.clear()
    r = client.post("/api/auth/login", json={"email": email, "password": "wrongpassword"})
    assert r.status_code == 401


def test_short_password_rejected(client):
    r = client.post("/api/auth/register", json={"email": "c@example.com", "password": "short"})
    assert r.status_code == 422


def test_change_password_requires_current(auth_client):
    r = auth_client.post(
        "/api/auth/change-password",
        json={"current_password": "wrong", "new_password": "anothersecret1"},
        headers=auth_client.csrf(),
    )
    assert r.status_code == 400


def test_password_is_hashed_not_plaintext():
    from app.db import SessionLocal
    from app.models import User
    from sqlalchemy import select

    db = SessionLocal()
    try:
        user = db.execute(select(User)).scalars().first()
        assert user is not None
        assert user.password_hash.startswith("$argon2id$")
        assert "supersecret1" not in user.password_hash
    finally:
        db.close()

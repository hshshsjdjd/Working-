from __future__ import annotations

import io
import uuid


def _new_client(client):
    email = f"u_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/auth/register", json={"email": email, "password": "supersecret1"})
    return client


def test_csrf_required_for_mutations(auth_client):
    # Missing CSRF header must be rejected even with a valid session cookie.
    r = auth_client.post("/api/conversations", json={"title": "x"})
    assert r.status_code == 403

    r2 = auth_client.post("/api/conversations", json={"title": "x"}, headers=auth_client.csrf())
    assert r2.status_code == 201


def test_idor_conversation_isolation(client):
    # User A creates a conversation.
    ea = f"a_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/auth/register", json={"email": ea, "password": "supersecret1"})
    csrf_a = {"X-CSRF-Token": client.cookies.get("nvai_csrf")}
    conv = client.post("/api/conversations", json={"title": "secret"}, headers=csrf_a).json()
    client.cookies.clear()

    # User B logs in and must not read A's conversation.
    eb = f"b_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/auth/register", json={"email": eb, "password": "supersecret1"})
    r = client.get(f"/api/conversations/{conv['id']}")
    assert r.status_code == 404
    r2 = client.get(f"/api/conversations/{conv['id']}/messages")
    assert r2.status_code == 404


def test_unauthenticated_access_blocked(client):
    client.cookies.clear()
    assert client.get("/api/conversations").status_code == 401
    assert client.get("/api/models").status_code == 401
    assert client.get("/api/settings").status_code == 401


def test_upload_rejects_executable(auth_client):
    files = {"file": ("evil.sh", io.BytesIO(b"#!/bin/sh\necho hi"), "text/plain")}
    r = auth_client.post("/api/files", files=files, headers=auth_client.csrf())
    assert r.status_code == 415


def test_upload_rejects_bad_mimetype(auth_client):
    files = {"file": ("a.bin", io.BytesIO(b"\x00\x01"), "application/octet-stream")}
    r = auth_client.post("/api/files", files=files, headers=auth_client.csrf())
    assert r.status_code == 415


def test_upload_path_traversal_name_is_sanitized(auth_client):
    files = {"file": ("../../etc/passwd", io.BytesIO(b"hello"), "text/plain")}
    r = auth_client.post("/api/files", files=files, headers=auth_client.csrf())
    assert r.status_code == 201
    body = r.json()
    assert "/" not in body["original_name"]
    assert ".." not in body["original_name"]


def test_file_size_limit(auth_client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "max_file_size", 10)
    big = io.BytesIO(b"x" * 100)
    files = {"file": ("big.txt", big, "text/plain")}
    r = auth_client.post("/api/files", files=files, headers=auth_client.csrf())
    assert r.status_code == 413


def test_api_key_never_exposed(auth_client):
    # No endpoint should ever return the configured NVIDIA key.
    for path in ["/api/auth/me", "/api/models", "/api/settings", "/api/usage", "/ready"]:
        r = auth_client.get(path)
        assert "test-key" not in r.text


def test_security_headers_present(client):
    r = client.get("/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert "Content-Security-Policy" in r.headers

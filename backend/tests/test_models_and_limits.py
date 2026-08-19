from __future__ import annotations


def test_only_enabled_models_listed(auth_client):
    models = auth_client.get("/api/models").json()
    ids = [m["id"] for m in models]
    assert "meta/llama-3.1-8b-instruct" in ids
    assert "disabled/model" not in ids


def test_auth_rate_limit(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "auth_max_attempts_per_minute", 3)
    codes = []
    for _ in range(5):
        r = client.post("/api/auth/login", json={"email": "none@example.com", "password": "whatever1"})
        codes.append(r.status_code)
    assert 429 in codes


def test_health_and_ready(client):
    assert client.get("/health").json()["status"] == "ok"
    ready = client.get("/ready").json()
    assert ready["database"] is True
    # nvidia_configured reflects presence of a key, never the key itself.
    assert isinstance(ready["nvidia_configured"], bool)


def test_admin_requires_role(auth_client):
    # A normal (non-first) user must be forbidden from admin endpoints.
    r = auth_client.get("/api/admin/stats")
    assert r.status_code in (403,)


def test_context_builder_preserves_system_and_last():
    from app.services.context import build_messages

    history = [{"role": "user", "content": "x" * 400}, {"role": "assistant", "content": "y" * 400},
               {"role": "user", "content": "final question"}]
    msgs = build_messages(system_prompt="be nice", history=history, max_context_tokens=60)
    assert msgs[0] == {"role": "system", "content": "be nice"}
    # The most recent user message is always retained.
    assert msgs[-1]["content"] == "final question"

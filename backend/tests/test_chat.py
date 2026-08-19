from __future__ import annotations

import json

import httpx
import respx

from app.config import settings

NVIDIA_URL = f"{settings.nvidia_base_url.rstrip('/')}/chat/completions"


def _sse_body() -> str:
    chunks = [
        {"choices": [{"delta": {"content": "Hello"}, "finish_reason": None}]},
        {"choices": [{"delta": {"content": " world"}, "finish_reason": "stop"}]},
        {"choices": [{"delta": {}, "finish_reason": "stop"}],
         "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7}},
    ]
    body = "".join(f"data: {json.dumps(c)}\n\n" for c in chunks)
    return body + "data: [DONE]\n\n"


def _make_conv(auth_client):
    return auth_client.post(
        "/api/conversations",
        json={"title": "New chat", "model_id": "meta/llama-3.1-8b-instruct"},
        headers=auth_client.csrf(),
    ).json()


@respx.mock
def test_chat_stream_end_to_end(auth_client):
    respx.post(NVIDIA_URL).mock(
        return_value=httpx.Response(200, text=_sse_body(),
                                    headers={"content-type": "text/event-stream"})
    )
    conv = _make_conv(auth_client)
    with auth_client.stream(
        "POST", "/api/chat/stream",
        json={"conversation_id": conv["id"], "content": "hi there"},
        headers=auth_client.csrf(),
    ) as r:
        assert r.status_code == 200
        collected = ""
        events = []
        for line in r.iter_lines():
            if line.startswith("data:"):
                evt = json.loads(line[5:].strip())
                events.append(evt)
                if evt["type"] == "delta":
                    collected += evt["content"]
    assert collected == "Hello world"
    assert any(e["type"] == "meta" for e in events)
    assert any(e["type"] == "done" for e in events)

    # The assistant message is persisted and retrievable.
    msgs = auth_client.get(f"/api/conversations/{conv['id']}/messages").json()
    roles = [m["role"] for m in msgs]
    assert roles == ["user", "assistant"]
    assert msgs[1]["content"] == "Hello world"
    # Title auto-generated from the first user message.
    conv_after = auth_client.get(f"/api/conversations/{conv['id']}").json()
    assert conv_after["title"] == "hi there"


@respx.mock
def test_chat_non_stream(auth_client):
    respx.post(NVIDIA_URL).mock(
        return_value=httpx.Response(200, json={
            "choices": [{"message": {"role": "assistant", "content": "42"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 1, "total_tokens": 4},
        })
    )
    conv = _make_conv(auth_client)
    r = auth_client.post(
        "/api/chat",
        json={"conversation_id": conv["id"], "content": "what is the answer?"},
        headers=auth_client.csrf(),
    )
    assert r.status_code == 200
    assert r.json()["content"] == "42"

    usage = auth_client.get("/api/usage").json()
    assert usage["total_requests"] >= 1
    assert usage["total_tokens"] >= 4


@respx.mock
def test_chat_upstream_error_maps_gracefully(auth_client):
    respx.post(NVIDIA_URL).mock(return_value=httpx.Response(401, json={"error": "bad key"}))
    conv = _make_conv(auth_client)
    r = auth_client.post(
        "/api/chat",
        json={"conversation_id": conv["id"], "content": "hello"},
        headers=auth_client.csrf(),
    )
    # 401 upstream is surfaced as a bad gateway, not a stack trace.
    assert r.status_code == 502
    assert "test-key" not in r.text


def test_chat_rejects_disabled_model(auth_client):
    conv = _make_conv(auth_client)
    r = auth_client.post(
        "/api/chat",
        json={"conversation_id": conv["id"], "content": "hi", "model_id": "disabled/model"},
        headers=auth_client.csrf(),
    )
    assert r.status_code == 400


def test_chat_requires_ownership(client):
    import uuid
    ea = f"a_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/auth/register", json={"email": ea, "password": "supersecret1"})
    conv = client.post("/api/conversations", json={"title": "x"},
                       headers={"X-CSRF-Token": client.cookies.get("nvai_csrf")}).json()
    client.cookies.clear()
    eb = f"b_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/auth/register", json={"email": eb, "password": "supersecret1"})
    r = client.post(
        "/api/chat",
        json={"conversation_id": conv["id"], "content": "hi"},
        headers={"X-CSRF-Token": client.cookies.get("nvai_csrf")},
    )
    assert r.status_code == 404

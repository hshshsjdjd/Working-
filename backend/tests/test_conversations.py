from __future__ import annotations


def test_conversation_crud(auth_client):
    created = auth_client.post(
        "/api/conversations", json={"title": "First"}, headers=auth_client.csrf()
    ).json()
    cid = created["id"]

    listed = auth_client.get("/api/conversations").json()
    assert any(c["id"] == cid for c in listed)

    updated = auth_client.patch(
        f"/api/conversations/{cid}",
        json={"title": "Renamed", "pinned": True},
        headers=auth_client.csrf(),
    ).json()
    assert updated["title"] == "Renamed"
    assert updated["pinned"] is True

    # Archive then verify it drops out of the default list.
    auth_client.patch(f"/api/conversations/{cid}", json={"archived": True}, headers=auth_client.csrf())
    active = auth_client.get("/api/conversations").json()
    assert all(c["id"] != cid for c in active)
    archived = auth_client.get("/api/conversations", params={"archived": True}).json()
    assert any(c["id"] == cid for c in archived)

    d = auth_client.delete(f"/api/conversations/{cid}", headers=auth_client.csrf())
    assert d.status_code == 204
    assert auth_client.get(f"/api/conversations/{cid}").status_code == 404


def test_conversation_search(auth_client):
    auth_client.post("/api/conversations", json={"title": "Weather report"}, headers=auth_client.csrf())
    auth_client.post("/api/conversations", json={"title": "Recipe ideas"}, headers=auth_client.csrf())
    res = auth_client.get("/api/conversations", params={"search": "weather"}).json()
    assert len(res) == 1
    assert res[0]["title"] == "Weather report"


def test_settings_roundtrip(auth_client):
    r = auth_client.get("/api/settings").json()
    assert r["theme"] == "amoled"
    upd = auth_client.patch(
        "/api/settings",
        json={"theme": "dark", "temperature": 0.3, "default_model_id": "meta/llama-3.1-8b-instruct"},
        headers=auth_client.csrf(),
    ).json()
    assert upd["theme"] == "dark"
    assert upd["temperature"] == 0.3

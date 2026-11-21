from __future__ import annotations


def test_health(client):
    r = client.get("/pokemon/api/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_bootstrap(client, headers):
    r = client.get("/pokemon/api/bootstrap", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["identity"]["user_id"] == headers["X-Pokemon-User"]
    assert data["profile"]["pokemon_count"] == 0
    assert data["menu"]


def test_menu(client, headers):
    r = client.get("/pokemon/api/menu", headers=headers)
    assert r.status_code == 200
    categories = r.json()["categories"]
    assert "基础" in categories
    assert any(e["func"] == "宝可梦帮助" for e in categories["基础"])


def test_command_flow(client, headers):
    r = client.post("/pokemon/api/command", headers=headers, json={"text": "领取初始精灵 小火龙"})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"], data
    assert data["text"]
    assert data["done"]

    r = client.post("/pokemon/api/command", headers=headers, json={"text": "精灵状态 小火龙"})
    assert r.status_code == 200
    assert r.json()["images"]


def test_chart(client, headers):
    client.post("/pokemon/api/command", headers=headers, json={"text": "领取初始精灵 小火龙"})
    r = client.get("/pokemon/api/charts/team_radar", headers=headers)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/png")
    assert r.content.startswith(b"\x89PNG")


def test_pokedex(client):
    r = client.get("/pokemon/api/pokedex", params={"name": "皮卡丘"})
    assert r.status_code == 200
    entry = r.json()["entry"]
    assert entry["id"] == 25
    assert "电" in entry["types"]


def test_leaderboard(client):
    r = client.get("/pokemon/api/leaderboard/score")
    assert r.status_code == 200
    assert "items" in r.json()


def test_index_page(client):
    r = client.get("/pokemon")
    assert r.status_code == 200
    assert "宝可梦 · QWeb" in r.text
    assert "__POKEMON_BASE__" not in r.text


def test_qweb_alias(client, headers):
    r = client.get("/qweb/pokemon/api/health", headers=headers)
    assert r.status_code == 200
    r = client.get("/qweb/admin/pokemon/api/health", headers=headers)
    assert r.status_code == 200


def test_ai_without_model(client, headers):
    r = client.post("/pokemon/api/ai/chat", headers=headers, json={"message": "我的队伍怎么样"})
    assert r.status_code == 200
    data = r.json()
    assert data["error"] in {"no_model", "disabled"}
    assert data["text"]


def test_admin_state_requires_admin(client, headers):
    r = client.get("/qweb/admin/pokemon/api/admin/state", headers=headers)
    assert r.status_code == 403


def test_admin_state_with_header(client, headers):
    admin_headers = dict(headers, **{"X-Pokemon-Is-Admin": "1"})
    r = client.get("/qweb/admin/pokemon/api/admin/state", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"]
    assert data["menu_entries"] >= 90
    assert "scheduler_jobs" in data


def test_admin_reload(client, headers):
    admin_headers = dict(headers, **{"X-Pokemon-Is-Admin": "1"})
    r = client.post("/qweb/admin/pokemon/api/admin/reload", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["ok"]


def test_qweb_secret(client, headers, monkeypatch):
    from nonebot_plugin_pokemon.config import plugin_config

    monkeypatch.setattr(plugin_config, "pokemon_qweb_secret", "s3cr3t")
    r = client.get("/qweb/pokemon/api/health", headers=headers)
    assert r.status_code == 401
    secured = dict(headers, **{"X-QWeb-Secret": "s3cr3t"})
    r = client.get("/qweb/pokemon/api/health", headers=secured)
    assert r.status_code == 200

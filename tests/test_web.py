from __future__ import annotations

import qweb_stub


def test_health_is_public(client):
    r = client.get("/qweb/pokemon/api/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_bootstrap_uses_host_account(client, headers, uid):
    r = client.get("/qweb/pokemon/api/bootstrap", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["identity"]["user_id"] == uid
    assert data["identity"]["is_admin"] is False
    assert data["identity"]["platform"] == "qweb"
    assert data["profile"]["pokemon_count"] == 0
    assert data["menu"]
    assert data["tools"]["count"] == 13


def test_menu(client, headers):
    r = client.get("/qweb/pokemon/api/menu", headers=headers)
    assert r.status_code == 200
    categories = r.json()["categories"]
    assert "基础" in categories
    assert any(e["func"] == "宝可梦帮助" for e in categories["基础"])


def completed(client, headers, result):
    import time

    deadline = time.monotonic() + 20
    while not result["done"]:
        assert time.monotonic() < deadline
        time.sleep(0.1)
        result = client.get("/qweb/pokemon/api/session", headers=headers,
                            params={"operation": result["operation"]}).json()
    assert result["ok"], result["error"]
    return result


def test_command_flow(client, headers):
    r = client.post("/qweb/pokemon/api/command", headers=headers, json={"text": "领取初始精灵 小火龙"})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"], data
    data = completed(client, headers, data)
    assert data["text"]
    assert data["done"]

    r = client.post("/qweb/pokemon/api/command", headers=headers, json={"text": "精灵状态 小火龙"})
    assert r.status_code == 200
    assert completed(client, headers, r.json())["images"]


def test_chart(client, headers):
    client.post("/qweb/pokemon/api/command", headers=headers, json={"text": "领取初始精灵 小火龙"})
    r = client.get("/qweb/pokemon/api/charts/team_radar", headers=headers)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/png")
    assert r.content.startswith(b"\x89PNG")


def test_pokedex(client, headers):
    r = client.get("/qweb/pokemon/api/pokedex", headers=headers, params={"name": "皮卡丘"})
    assert r.status_code == 200
    entry = r.json()["entry"]
    assert entry["id"] == 25
    assert "电" in entry["types"]


def test_leaderboard(client, headers):
    r = client.get("/qweb/pokemon/api/leaderboard/score", headers=headers)
    assert r.status_code == 200
    assert "items" in r.json()


def test_index_page(client, headers):
    r = client.get("/qweb/pokemon", headers=headers)
    assert r.status_code == 200
    assert "宝可梦 · QWeb" in r.text
    assert "__POKEMON_BASE__" not in r.text
    # 页面不再声明身份，也不再内置直连 AI。
    assert "X-Pokemon-User" not in r.text
    assert "X-QWeb-Is-Admin" not in r.text
    assert 'id="screen"' in r.text and 'id="command-input"' not in r.text
    assert '<script src="/qweb/pokemon/static/app.js"></script>' in r.text
    assert "<script>" not in r.text
    script = client.get("/qweb/pokemon/static/app.js", headers=headers)
    assert script.status_code == 200
    assert "/qweb/api/v1/auth/session" in script.text and "X-CSRF-Token" in script.text
    assert "/api/ai/chat" not in r.text
    assert "AI 助手" not in r.text


def test_qweb_alias(client, headers):
    r = client.get("/qweb/pokemon/api/health", headers=headers)
    assert r.status_code == 200
    r = client.get("/qweb/admin/pokemon/api/health", headers=headers)
    assert r.status_code == 200


def test_no_direct_ai_route(client, headers):
    r = client.post(
        "/qweb/pokemon/api/ai/chat",
        headers=headers,
        json={"message": "我的队伍怎么样"},
    )
    assert r.status_code == 404


def test_missing_membership_rejected(client):
    r = client.get("/qweb/pokemon/api/bootstrap")
    assert r.status_code == 401


def test_missing_membership_rejected_on_page(client):
    r = client.get("/qweb/pokemon")
    assert r.status_code == 401


def test_missing_csrf_rejected(client, uid):
    headers = {"X-Test-Account": f"member:{uid}"}
    r = client.post("/qweb/pokemon/api/command", headers=headers, json={"text": "宝可梦帮助"})
    assert r.status_code == 403


def test_wrong_csrf_rejected(client, uid):
    headers = {"X-Test-Account": f"member:{uid}", "X-CSRF-Token": "wrong"}
    r = client.post("/qweb/pokemon/api/command", headers=headers, json={"text": "宝可梦帮助"})
    assert r.status_code == 403


def test_admin_state_requires_admin(client, headers):
    r = client.get("/qweb/admin/pokemon/api/admin/state", headers=headers)
    assert r.status_code == 403

    r = client.get("/qweb/pokemon/api/admin/state", headers=headers)
    assert r.status_code == 403


def test_admin_prefix_requires_admin_for_all_api(client, headers, admin_headers):
    r = client.get("/qweb/admin/pokemon/api/bootstrap", headers=headers)
    assert r.status_code == 403
    r = client.get("/qweb/admin/pokemon/api/bootstrap", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["identity"]["is_admin"] is True


def test_admin_state_with_admin_account(client, admin_headers):
    r = client.get("/qweb/admin/pokemon/api/admin/state", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"]
    assert data["menu_entries"] >= 90
    assert data["tools_count"] == 13
    assert "scheduler_jobs" in data


def test_admin_reload_requires_csrf(client, admin_headers):
    headers = dict(admin_headers)
    headers.pop("X-CSRF-Token")
    r = client.post("/qweb/admin/pokemon/api/admin/reload", headers=headers)
    assert r.status_code == 403

    r = client.post("/qweb/admin/pokemon/api/admin/reload", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["ok"]


def test_client_cannot_declare_identity_or_admin(client, headers, uid):
    spoofed = dict(headers)
    spoofed.update(
        {
            "X-Pokemon-User": "evil-user",
            "X-Pokemon-User-Name": "evil",
            "X-Pokemon-Is-Admin": "1",
            "X-QWeb-User-Id": "evil-user",
            "X-QWeb-Is-Admin": "1",
        }
    )
    r = client.get(
        "/qweb/pokemon/api/bootstrap",
        headers=spoofed,
        params={"user_id": "evil-user", "is_admin": "1"},
        cookies={"pokemon_uid": "evil-user"},
    )
    assert r.status_code == 200
    identity = r.json()["identity"]
    assert identity["user_id"] == uid
    assert identity["is_admin"] is False

    r = client.get("/qweb/pokemon/api/admin/state", headers=spoofed)
    assert r.status_code == 403


def test_client_cannot_declare_identity_in_command_payload(client, headers, uid):
    r = client.post(
        "/qweb/pokemon/api/command",
        headers=headers,
        json={
            "text": "领取初始精灵 小火龙",
            "user_id": "evil-user",
            "is_admin": True,
            "role": "admin",
            "group_id": "evil-group",
        },
    )
    assert r.status_code == 200
    assert r.json()["ok"]
    assert r.json()["session"]["user_id"] == uid

    r = client.get("/qweb/pokemon/api/bootstrap", headers=headers)
    assert r.json()["profile"]["pokemon_count"] == 1
    # 命令没有落到请求体里的“evil-user”。
    evil = client.get(
        "/qweb/pokemon/api/player",
        headers=dict(headers, **{"X-Test-Account": f"admin:{uid}"}),
        params={"uid": "evil-user"},
    )
    assert evil.status_code == 200
    assert evil.json()["profile"]["pokemon_count"] == 0


def test_qweb_secret_config_removed(client, headers):
    from nonebot_plugin_pokemon.config import plugin_config

    assert not hasattr(plugin_config, "pokemon_qweb_secret")
    r = client.get("/qweb/pokemon/api/health", headers=headers)
    assert r.status_code == 200


def test_stub_csrf_token_is_required(client, headers):
    # 防御性自检：测试宿主确实校验 token，避免“正常授权”测试假通过。
    assert headers["X-CSRF-Token"] == qweb_stub.CSRF_TOKEN

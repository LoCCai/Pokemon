from __future__ import annotations

import time
from pathlib import Path

from nonebot_plugin_pokemon.paths import pokemon_data_dir


def wait_done(client, headers, result, timeout: float = 20.0):
    deadline = time.monotonic() + timeout
    while not result.get("done"):
        assert time.monotonic() < deadline
        time.sleep(0.1)
        result = client.get(
            "/qweb/pokemon/api/session",
            headers=headers,
            params={"operation": result.get("operation", ""), "offset": result.get("offset", 0)},
        ).json()
    return result


def test_world_requires_membership(client):
    assert client.get("/qweb/pokemon/api/game/world").status_code == 401


def test_world_contract_from_saved_account(client, headers, uid):
    r = client.get("/qweb/pokemon/api/game/world", headers=headers)
    assert r.status_code == 200
    data = r.json()
    for key in ("profile", "starters", "owned", "locations", "items", "current", "regions"):
        assert key in data
    assert data["profile"]["uid"] == uid
    assert data["profile"]["pokemon_count"] == 0
    assert data["owned"] == []
    assert data["current"]["started"] is False
    starter = next(item for item in data["starters"] if item["name"] == "小火龙")
    assert starter["id"] == 4
    assert starter["types"]
    assert starter["region"] == "关东"
    assert starter["sprite"].endswith("/api/game/sprite/4")
    assert any(item["name"] == "真新镇" and item["region"] == "关东" for item in data["locations"])
    assert isinstance(data["items"], list)


def test_action_claim_then_world_and_stale_replay(client, headers, uid):
    r = client.post(
        "/qweb/pokemon/api/game/action",
        headers=headers,
        json={"action": "claim", "value": "小火龙"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"], data
    assert data["action"] == "claim"
    assert data["session"]["user_id"] == uid
    assert "state" in data and "options" in data
    token = data["operation"]
    assert token

    world = client.get("/qweb/pokemon/api/game/world", headers=headers).json()
    assert world["profile"]["pokemon_count"] == 1
    assert world["owned_total"] == 1
    mon = world["owned"][0]
    assert mon["name"] == "小火龙"
    assert mon["level"] >= 1
    assert mon["moves"]
    assert world["current"]["started"] is True
    assert world["current"]["map"]
    assert any(item["name"] == world["current"]["map"] and item["current"] for item in world["locations"])

    # Replaying the already-consumed turn must be rejected.
    replay = client.post(
        "/qweb/pokemon/api/game/action",
        headers=headers,
        json={"action": "claim", "value": "小火龙"},
    )
    assert replay.status_code == 409, replay.text
    assert replay.json()["stale"] is True


def test_action_identity_fields_are_ignored(client, headers, uid):
    r = client.post(
        "/qweb/pokemon/api/game/action",
        headers=headers,
        json={
            "action": "claim",
            "value": "妙蛙种子",
            "user_id": "evil-user",
            "is_admin": True,
            "cost": 0,
            "command": "宝可梦重开",
            "text": "宝可梦重开",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["session"]["user_id"] == uid
    world = client.get("/qweb/pokemon/api/game/world", headers=headers).json()
    assert world["profile"]["pokemon_count"] == 1
    assert world["owned"][0]["name"] == "妙蛙种子"


def test_action_unknown_and_arbitrary_values_rejected(client, headers):
    r = client.post("/qweb/pokemon/api/game/action", headers=headers, json={"action": "run_command", "value": "whoami"})
    assert r.status_code == 400

    r = client.post("/qweb/pokemon/api/game/action", headers=headers, json={"action": "travel", "value": "rm -rf /"})
    assert r.status_code == 400

    r = client.post("/qweb/pokemon/api/game/action", headers=headers, json={"action": "claim", "value": "皮卡丘"})
    assert r.status_code == 400


def test_action_requires_csrf(client, uid):
    headers = {"X-Test-Account": f"member:{uid}"}
    r = client.post("/qweb/pokemon/api/game/action", headers=headers, json={"action": "explore"})
    assert r.status_code == 403


def test_action_party_and_invalid_region_do_not_escape_allowlist(client, headers):
    claim = client.post(
        "/qweb/pokemon/api/game/action",
        headers=headers,
        json={"action": "claim", "value": "杰尼龟"},
    )
    assert claim.status_code == 200, claim.text
    token, offset = claim.json()["operation"], claim.json()["offset"]

    party = client.post(
        "/qweb/pokemon/api/game/action",
        headers=headers,
        json={"action": "party", "value": "杰尼龟", "operation": token, "offset": offset},
    )
    assert party.status_code == 200, party.text
    assert party.json()["state"]["phase"] in {"running", "done", "awaiting"}

    token, offset = party.json()["operation"], party.json()["offset"]
    bad = client.post(
        "/qweb/pokemon/api/game/action",
        headers=headers,
        json={"action": "choose_region", "value": "不存在地区", "operation": token, "offset": offset},
    )
    assert bad.status_code == 400


def test_sprite_fallback_is_deterministic_and_member_only(client, headers):
    assert client.get("/qweb/pokemon/api/game/sprite/25").status_code == 401
    first = client.get("/qweb/pokemon/api/game/sprite/132", headers=headers)
    second = client.get("/qweb/pokemon/api/game/sprite/132", headers=headers)
    assert first.status_code == 200
    assert first.content.startswith(b"\x89PNG")
    assert first.content == second.content
    assert first.headers["X-Pokemon-Sprite"] == "fallback"
    assert client.get("/qweb/pokemon/api/game/sprite/999999", headers=headers).status_code == 404


def test_sprite_serves_genuine_local_icon(client, headers):
    icon_dir = pokemon_data_dir() / "resource" / "icon"
    icon_dir.mkdir(parents=True, exist_ok=True)
    path = icon_dir / "皮卡丘.png"
    payload = b"\x89PNG\r\n\x1a\n-local-test"
    path.write_bytes(payload)
    try:
        r = client.get("/qweb/pokemon/api/game/sprite/25", headers=headers)
        assert r.status_code == 200
        assert r.content == payload
        assert r.headers["X-Pokemon-Sprite"] == "local"
    finally:
        path.unlink(missing_ok=True)


def test_new_static_assets_are_served_and_path_access_is_narrow(client, headers):
    for name, kind in (
        ("app.js", "javascript"),
        ("qweb-theme.js", "javascript"),
        ("game.css", "text/css"),
        ("game.js", "javascript"),
    ):
        r = client.get(f"/qweb/pokemon/static/{name}", headers=headers)
        assert r.status_code == 200, (name, r.status_code)
        assert kind in r.headers["content-type"]
    assert client.get("/qweb/pokemon/static/qweb-theme.js").status_code == 401
    assert client.get("/qweb/pokemon/static/../app.py", headers=headers).status_code == 404
    assert client.get("/qweb/pokemon/static/__init__.py", headers=headers).status_code == 404


def test_live_manual_battle_exposes_true_hp_and_clickable_moves(client, headers, monkeypatch):
    import nonebot_plugin_pokemon.Pokemon.pokemon_duel.map as game_map

    r = client.post(
        "/qweb/pokemon/api/game/action",
        headers=headers,
        json={"action": "claim", "value": "小火龙"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    token = data["operation"]

    offset = data["offset"]

    # Force the real explore encounter branch; the core still rolls all damage.
    monkeypatch.setattr(game_map.random, "uniform", lambda a, b: (float(a) + float(b)) / 2.0)
    r = client.post(
        "/qweb/pokemon/api/game/action",
        headers=headers,
        json={"action": "explore", "operation": token, "offset": offset},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    deadline = time.monotonic() + 10
    while not data.get("awaiting") and not data.get("done"):
        assert time.monotonic() < deadline
        time.sleep(0.1)
        data = client.get(
            "/qweb/pokemon/api/session",
            headers=headers,
            params={"operation": data["operation"], "offset": data["offset"]},
        ).json()
    assert data["awaiting"] is True, data
    battle = data["state"]["battle"]
    assert battle["player"]["name"] == "小火龙"
    assert battle["player"]["hp"] <= battle["player"]["max_hp"]
    assert battle["opponent"]["name"]
    assert battle["opponent"]["level"] >= 1
    assert battle["moves"]
    option = next(item for item in data["options"] if item["kind"] == "move")
    assert option["action"] == "reply"
    assert option["value"] in battle["moves"]

    result = client.post(
        "/qweb/pokemon/api/game/action",
        headers=headers,
        json={
            "action": "reply",
            "value": option["value"],
            "operation": data["operation"],
            "offset": data["offset"],
        },
    )
    assert result.status_code == 200, result.text
    assert result.json()["state"]["phase"] in {"awaiting", "running", "done"}
    # The old reply turn is now stale even though the token was current before.
    replay = client.post(
        "/qweb/pokemon/api/game/action",
        headers=headers,
        json={
            "action": "reply",
            "value": option["value"],
            "operation": data["operation"],
            "offset": data["offset"],
        },
    )
    assert replay.status_code == 409, replay.text

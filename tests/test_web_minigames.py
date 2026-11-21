"""End-to-end QWeb tests for the five real ``pokemon_whois`` minigames.

Answers are read from the real handlers' own state and submitted through the
public QWeb action API.  The tests assert real native prompts, images, timers,
rewards and cleanup; nothing here fabricates a win or a hint.
"""

from __future__ import annotations

import time

import pytest

from nonebot_plugin_pokemon.Pokemon.pokemon_whois import (
    CHARA_NAME,
    winner_judger,
    winner_judger_cc,
    winner_judger_jn,
    winner_judger_sx,
    winner_judger_tj,
)
from nonebot_plugin_pokemon.Pokemon.utils.dbbase.storage import fetchone_sync
from nonebot_plugin_pokemon.game.minigames import (
    MINIGAME_GAMES,
    scope_for,
    judges,
)
from nonebot_plugin_pokemon.platform.interaction import broker
from nonebot_plugin_pokemon.web.session import registry


GAME_JUDGERS = {
    "我是谁": winner_judger,
    "猜图鉴": winner_judger_tj,
    "猜精灵": winner_judger_cc,
}


def answer_for(uid: str, game: str) -> str:
    scope = scope_for(uid)
    if game in GAME_JUDGERS:
        pid = GAME_JUDGERS[game].get_correct_chara_id(scope)
        return CHARA_NAME[pid][0]
    if game == "猜技能":
        return winner_judger_jn.get_correct_jineng(scope)
    if game == "猜属性":
        return " ".join(winner_judger_sx.get_correct_shuxlist(scope))
    raise AssertionError(game)


def start(client, headers, game: str, previous=None):
    payload = {"action": "minigame_start", "value": game}
    if previous is not None:
        payload["operation"] = previous["operation"]
        payload["offset"] = previous["offset"]
    r = client.post(
        "/qweb/pokemon/api/game/action",
        headers=headers,
        json=payload,
    )
    assert r.status_code == 200, r.text
    return r.json()


def guess(client, headers, data, value, *, action="minigame_guess"):
    r = client.post(
        "/qweb/pokemon/api/game/action",
        headers=headers,
        json={
            "action": action,
            "value": value,
            "operation": data["operation"],
            "offset": data["offset"],
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def poll(client, headers, data, timeout: float = 10.0):
    deadline = time.monotonic() + timeout
    while not data.get("done"):
        assert time.monotonic() < deadline, data
        time.sleep(0.05)
        data = client.get(
            "/qweb/pokemon/api/session",
            headers=headers,
            params={"operation": data.get("operation", ""), "offset": data.get("offset", 0)},
        ).json()
    return data


def scope_is_on(scope):
    return any(judge.get_on_off_status(scope) for judge in judges())


def db_value(sql, args):
    row = fetchone_sync(sql, args)
    return row[0] if row else 0


def score(uid: str) -> int:
    return int(db_value("select score from pokemon_score where uid=?", (uid,)))


def game_count(uid: str, kind: str) -> int:
    return int(db_value("select num from pokemon_game where uid=? and type=?", (uid, kind)))


def assert_clean(uid: str, data) -> None:
    scope = scope_for(uid)
    assert not scope_is_on(scope)
    assert None not in winner_judger.on
    assert None not in winner_judger_cc.on
    assert None not in winner_judger_sx.on
    assert None not in winner_judger_jn.on
    assert None not in winner_judger_tj.on
    session = registry.get(uid)
    if session.event is not None:
        assert not broker.has_waiter(session.event.scene_key)
    assert data["minigame"]["phase"] != "awaiting"


def test_minigame_start_exposes_real_prompt_image_and_typed_actions(client, headers, uid):
    data = start(client, headers, "我是谁")
    assert data["awaiting"] is True, data
    assert data["minigame"]["game"] == "我是谁"
    assert data["minigame"]["phase"] == "awaiting"
    assert data["minigame"]["prompt"]
    assert data["images"]
    actions = {item["action"] for item in data["minigame"]["allowed_actions"]}
    assert {"minigame_guess", "cancel"} <= actions
    assert any(item["action"] == "minigame_guess" for item in data["options"])
    # The answer is deliberately absent from the waiting snapshot.
    answer = answer_for(uid, "我是谁")
    assert answer not in str(data["minigame"])
    red = guess(client, headers, data, answer)
    assert red["done"] or red["awaiting"] is False
    done = poll(client, headers, red)
    assert done["done"] is True
    assert "正确答案是" in done["text"]
    assert answer in done["text"]
    assert done["minigame"]["phase"] == "done"
    assert score(uid) == 1000
    assert game_count(uid, "whois") == 1
    assert_clean(uid, done)


@pytest.mark.parametrize(
    ("game", "kind"),
    [("猜图鉴", "whotj"), ("猜技能", "whojn"), ("猜属性", "whosx"), ("猜精灵", "whocc")],
)
def test_each_real_handler_reaches_real_reward(client, headers, uid, game, kind):
    data = start(client, headers, game)
    assert data["awaiting"] is True, data
    assert data["minigame"]["game"] == game
    assert data["minigame"]["prompt"]
    answer = answer_for(uid, game)
    result = guess(client, headers, data, answer)
    done = poll(client, headers, result)
    assert done["done"] is True
    assert "正确答案是" in done["text"]
    assert answer in done["text"]
    assert score(uid) == 1000
    assert game_count(uid, kind) == 1
    assert_clean(uid, done)


def test_guess_pokemon_supports_multiple_sequential_guesses(client, headers, uid):
    data = start(client, headers, "猜精灵")
    assert data["awaiting"] is True, data
    answer = answer_for(uid, "猜精灵")
    first = guess(client, headers, data, "绝对不是这只")
    assert first["awaiting"] is True, first
    assert first["minigame"]["game"] == "猜精灵"
    assert_clean_waiting = scope_is_on(scope_for(uid))
    assert assert_clean_waiting is True
    second = guess(client, headers, first, "仍然不是这只")
    assert second["awaiting"] is True, second
    third = guess(client, headers, second, answer)
    done = poll(client, headers, third)
    assert done["done"] is True
    assert answer in done["text"]
    assert "正确答案是" in done["text"]
    assert score(uid) == 1000
    assert_clean(uid, done)


def test_two_web_accounts_have_separate_native_state(client, headers, uid):
    other = f"{uid}-other"
    other_headers = {"X-Test-Account": f"member:{other}", "X-CSRF-Token": headers["X-CSRF-Token"]}
    a = start(client, headers, "猜图鉴")
    b = start(client, other_headers, "猜图鉴")
    assert a["awaiting"] and b["awaiting"]
    scope_a, scope_b = scope_for(uid), scope_for(other)
    assert scope_a != scope_b != "None"
    assert winner_judger_tj.get_on_off_status(scope_a)
    assert winner_judger_tj.get_on_off_status(scope_b)

    answer_a = answer_for(uid, "猜图鉴")
    answer_b = answer_for(other, "猜图鉴")
    done_a = poll(client, headers, guess(client, headers, a, answer_a))
    assert done_a["done"] is True
    assert answer_a in done_a["text"]

    # A's correct answer must not end, answer or consume B's round.
    assert winner_judger_tj.get_on_off_status(scope_b)
    session_b = registry.get(other)
    assert broker.has_waiter(session_b.event.scene_key)
    b_status = client.get(
        "/qweb/pokemon/api/session",
        headers=other_headers,
        params={"operation": b["operation"], "offset": 0},
    ).json()
    assert b_status["awaiting"] is True
    assert b_status["minigame"]["game"] == "猜图鉴"

    done_b = poll(client, other_headers, guess(client, other_headers, b, answer_b))
    assert done_b["done"] is True
    assert answer_b in done_b["text"]
    assert score(uid) == 1000
    assert score(other) == 1000
    assert_clean(uid, done_a)
    assert_clean(other, done_b)


def test_cancel_mid_round_cleans_real_state_and_allows_new_round(client, headers, uid):
    data = start(client, headers, "我是谁")
    scope = scope_for(uid)
    assert scope_is_on(scope)
    session = registry.get(uid)
    scene = session.event.scene_key
    assert broker.has_waiter(scene)

    r = client.post(
        "/qweb/pokemon/api/game/action",
        headers=headers,
        json={"action": "cancel", "operation": data["operation"], "offset": data["offset"]},
    )
    assert r.status_code == 200, r.text
    canceled = r.json()
    assert canceled["canceled"] is True
    assert canceled["awaiting"] is False
    assert not scope_is_on(scope)
    assert not broker.has_waiter(scene)
    assert not session.minigame_scope

    # Starting the same native command again must not hit "此轮游戏还没结束".
    again = start(client, headers, "我是谁", previous=canceled)
    assert again["awaiting"] is True, again
    assert "此轮游戏还没结束" not in again["text"]
    answer = answer_for(uid, "我是谁")
    done = poll(client, headers, guess(client, headers, again, answer))
    assert done["done"] is True
    assert_clean(uid, done)


def test_native_timeout_cleans_state(client, headers, uid, monkeypatch):
    import nonebot_plugin_pokemon.Pokemon.pokemon_whois as whois

    monkeypatch.setattr(whois, "ONE_TURN_TIME", 0.15)
    data = start(client, headers, "我是谁")
    assert data["awaiting"] is True, data
    done = poll(client, headers, data, timeout=5.0)
    assert done["done"] is True
    assert "没有人答对" in done["text"]
    assert_clean(uid, done)


def test_skill_hints_run_on_real_timers_and_timeout_cleans(client, headers, uid, monkeypatch):
    import async_timeout
    import nonebot_plugin_pokemon.Pokemon.pokemon_whois as whois

    monkeypatch.setattr(whois, "timeout", lambda _seconds: async_timeout.timeout(0.05))
    data = start(client, headers, "猜技能")
    done = poll(client, headers, data, timeout=10.0)
    assert done["done"] is True
    assert len(done["minigame"]["hints"]) == 6, done["minigame"]
    assert all(hint.startswith("提示") for hint in done["minigame"]["hints"])
    assert "没有人答对" in done["text"]
    assert "正确答案是" in done["text"]
    assert_clean(uid, done)


def test_guess_pokemon_hint_action_returns_only_revealed_native_hints(client, headers, uid, monkeypatch):
    import async_timeout
    import nonebot_plugin_pokemon.Pokemon.pokemon_whois as whois

    # Let the real handler publish the first hint, then stall before the second.
    monkeypatch.setattr(whois, "timeout", lambda _seconds: async_timeout.timeout(30))
    data = start(client, headers, "猜精灵")
    assert data["awaiting"] is True, data
    assert data["minigame"]["hint_available"] is True
    assert any(item["action"] == "minigame_hint" for item in data["minigame"]["allowed_actions"])
    r = client.post(
        "/qweb/pokemon/api/game/action",
        headers=headers,
        json={
            "action": "minigame_hint",
            "operation": data["operation"],
            "offset": data["offset"],
        },
    )
    assert r.status_code == 200, r.text
    hinted = r.json()
    assert hinted["minigame"]["game"] == "猜精灵"
    assert hinted["minigame"]["hints"]
    assert "[0]" not in str(hinted["minigame"])
    answer = answer_for(uid, "猜精灵")
    done = poll(client, headers, guess(client, headers, hinted, answer))
    assert done["done"] is True
    assert answer in done["text"]
    assert_clean(uid, done)


def test_command_endpoint_uses_same_isolated_session_snapshots(client, headers, uid):
    r = client.post(
        "/qweb/pokemon/api/command",
        headers=headers,
        json={"text": "/我是谁"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["awaiting"] is True, data
    assert data["minigame"]["game"] == "我是谁"
    assert scope_is_on(scope_for(uid))
    answer = answer_for(uid, "我是谁")
    r = client.post(
        "/qweb/pokemon/api/command",
        headers=headers,
        json={"text": answer},
    )
    assert r.status_code == 200, r.text
    done = poll(client, headers, r.json())
    assert done["done"] is True
    assert answer in done["text"]
    assert_clean(uid, done)


def test_reset_action_uses_real_native_reset_and_clears(client, headers, uid):
    data = start(client, headers, "猜属性")
    assert data["awaiting"] is True, data
    r = client.post(
        "/qweb/pokemon/api/game/action",
        headers=headers,
        json={
            "action": "minigame_reset",
            "operation": data["operation"],
            "offset": data["offset"],
        },
    )
    assert r.status_code == 200, r.text
    reset = r.json()
    assert "重置成功" in reset["text"]
    assert "此轮游戏还没结束" not in reset["text"]
    assert not scope_is_on(scope_for(uid))
    starts = {item["value"] for item in reset["allowed_actions"] if item["action"] == "minigame_start"}
    assert starts == set(MINIGAME_GAMES)

def test_web_ai_opens_the_same_round_as_the_game_page(client, headers, uid):
    from nonebot_plugin_pokemon.llm.tools import ToolContextData, _command

    async def open_quiz():
        return await _command(command="猜技能", _ctx=ToolContextData(user_id=uid, platform="qweb"))
    outcome = client.portal.call(open_quiz)
    assert outcome.structured["continue_url"] == "/qweb/pokemon"
    active = client.get("/qweb/pokemon/api/session", headers=headers).json()
    assert active["minigame"]["game"] == "猜技能" and active["awaiting"]
    done = poll(client, headers, guess(client, headers, active, answer_for(uid, "猜技能")))
    assert done["done"] and score(uid) == 1000

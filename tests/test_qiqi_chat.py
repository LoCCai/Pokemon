from __future__ import annotations

import pytest

from nonebot_plugin_pokemon import qiqi_chat


def test_host_inventory_tool_is_read_only():
    definitions = qiqi_chat.definitions()
    assert len(definitions) == 14
    assert definitions["pokemon_inventory"].effect == "read_only"
    assert "pokemon_command" in definitions


async def test_call_read_only_uses_bound_qq(uid):
    text, structured, images = await qiqi_chat.call(
        "pokemon_player_profile",
        {},
        qq=uid,
        thread="thread-1",
        role="member",
    )
    assert "金币" in text
    assert structured["pokemon_count"] == 0
    assert images == []


async def test_call_mutating_requires_confirmation(uid):
    with pytest.raises(ValueError, match="确认"):
        await qiqi_chat.call(
            "pokemon_command",
            {"command": "领取初始精灵 小火龙"},
            qq=uid,
            thread="thread-1",
            role="member",
            confirmed=False,
        )

    text, _, _ = await qiqi_chat.call(
        "pokemon_command",
        {"command": "领取初始精灵 小火龙"},
        qq=uid,
        thread="thread-1",
        role="member",
        confirmed=True,
    )
    assert "恭喜" in text


async def test_call_missing_qq_rejected():
    with pytest.raises(ValueError, match="QQ"):
        await qiqi_chat.call("pokemon_player_profile", {}, qq="", thread="thread-1")


async def test_call_role_beats_legacy_is_admin(uid):
    with pytest.raises(ValueError, match="权限"):
        await qiqi_chat.call(
            "pokemon_command",
            {"command": "刷新每日大量出现"},
            qq=uid,
            thread="thread-1",
            role="member",
            is_admin=True,
            confirmed=True,
        )

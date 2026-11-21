from __future__ import annotations

import pytest

from nonebot_plugin_pokemon.game import repository
from nonebot_plugin_pokemon.game.runner import run_and_format, run_command


async def test_claim_and_profile(uid):
    r = await run_command("领取初始精灵 小火龙", user_id=uid)
    assert r.ok and r.matched, r.error
    assert "恭喜" in r.text
    profile = await repository.profile(uid)
    assert profile["pokemon_count"] == 1
    assert profile["map"]


async def test_status_and_list(uid):
    await run_command("领取初始精灵 小火龙", user_id=uid)
    status = await run_command("精灵状态 小火龙", user_id=uid)
    assert status.ok
    assert status.images  # 绘图输出
    listing = await run_command("我的精灵列表", user_id=uid)
    assert listing.ok
    assert "小火龙" in listing.text


async def test_unknown_command(uid):
    r = await run_command("完全不存在的宝可梦指令", user_id=uid)
    assert not r.ok
    assert not r.matched


async def test_admin_command_denied(uid):
    r = await run_command("刷新每日大量出现", user_id=uid)
    assert r.denied
    assert not r.ok


async def test_chart_data(uid):
    from nonebot_plugin_pokemon.game import analytics, charts

    await run_command("领取初始精灵 小火龙", user_id=uid)
    profile = await repository.profile(uid)
    analysis = analytics.team_analysis(profile["team"])
    data = charts.team_radar(analysis)
    assert data.startswith(b"\x89PNG")
    data_url = charts.to_data_url(data)
    assert data_url.startswith("data:image/png;base64,")


async def test_run_and_format(uid):
    await run_command("领取初始精灵 小火龙", user_id=uid)
    text = await run_and_format("精灵状态 小火龙", user_id=uid)
    assert "小火龙" in text or "图片" in text


async def test_team_analysis_insights(uid):
    await run_command("领取初始精灵 小火龙", user_id=uid)
    profile = await repository.profile(uid)
    from nonebot_plugin_pokemon.game.analytics import team_analysis

    analysis = team_analysis(profile["team"])
    assert analysis["team_size"] == 1
    assert analysis["weaknesses"]
    assert analysis["insights"]

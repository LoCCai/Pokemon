from __future__ import annotations

import pytest

from nonebot_plugin_pokemon.game import repository
from nonebot_plugin_pokemon.game.runner import run_command
from nonebot_plugin_pokemon.llm.tools import (
    TOOL_MAP,
    TOOLS,
    ToolContextData,
    execute_tool,
    openai_tool_schemas,
)


def test_tool_schemas():
    schemas = openai_tool_schemas()
    assert len(schemas) == len(TOOLS) >= 12
    for schema in schemas:
        function = schema["function"]
        assert schema["type"] == "function"
        assert function["parameters"]["type"] == "object"
        assert function["description"]


@pytest.mark.parametrize(
    "name",
    [
        "pokemon_help_search",
        "pokemon_player_profile",
        "pokemon_dex_lookup",
        "pokemon_move_lookup",
        "pokemon_item_lookup",
        "pokemon_type_chart",
        "pokemon_team_analysis",
        "pokemon_global_overview",
        "pokemon_leaderboard",
        "pokemon_chart",
        "pokemon_player_report",
        "pokemon_command",
    ],
)
def test_tool_registered(name):
    assert name in TOOL_MAP


async def test_help_search():
    out = await execute_tool("pokemon_help_search", {"query": "对战"}, ToolContextData(user_id="u"))
    assert "对战" in out.text or out.structured
    assert out.structured["entries"]


async def test_profile_tool(uid):
    await run_command("领取初始精灵 小火龙", user_id=uid)
    out = await execute_tool("pokemon_player_profile", {}, ToolContextData(user_id=uid))
    assert "金币" in out.text
    assert out.structured["pokemon_count"] == 1


async def test_dex_tool():
    out = await execute_tool("pokemon_dex_lookup", {"name": "皮卡丘"}, ToolContextData())
    assert "皮卡丘" in out.text
    assert out.structured["id"] == 25


async def test_type_chart_tool():
    out = await execute_tool(
        "pokemon_type_chart",
        {"attack_type": "水", "defender_types": ["火"]},
        ToolContextData(),
    )
    assert "x2" in out.text


async def test_chart_tool(uid):
    await run_command("领取初始精灵 小火龙", user_id=uid)
    out = await execute_tool("pokemon_chart", {"kind": "team_radar"}, ToolContextData(user_id=uid))
    assert out.images and out.images[0].startswith("data:image/png;base64,")


async def test_command_tool(uid):
    out = await execute_tool(
        "pokemon_command",
        {"command": "领取初始精灵 小火龙"},
        ToolContextData(user_id=uid),
    )
    assert "恭喜" in out.text
    profile = await repository.profile(uid)
    assert profile["pokemon_count"] == 1


async def test_admin_tool_denied(uid):
    out = await execute_tool(
        "pokemon_command",
        {"command": "刷新每日大量出现"},
        ToolContextData(user_id=uid, is_admin=False),
    )
    assert "权限" in out.text or "管理员" in out.text


async def test_agent_tool_loop(monkeypatch, uid):
    from nonebot_plugin_pokemon.llm import agent

    await run_command("领取初始精灵 小火龙", user_id=uid)
    calls = []

    async def fake_completion(endpoint, messages, tools):
        calls.append(messages)
        if len(calls) == 1:
            return {
                "content": "我先查一下你的档案。",
                "tool_calls": [
                    {
                        "id": "call-1",
                        "type": "function",
                        "function": {"name": "pokemon_player_profile", "arguments": "{}"},
                    }
                ],
            }
        return {"content": "你的档案已经查到了。"}

    monkeypatch.setattr(agent, "resolve_endpoint", lambda: ("http://example.invalid/v1", "k", "test-model"))
    monkeypatch.setattr(agent, "_chat_completion", fake_completion)
    reply = await agent.run_agent("看看我的档案", ToolContextData(user_id=uid))
    assert reply.text == "你的档案已经查到了。"
    assert reply.tools_used and reply.tools_used[0]["name"] == "pokemon_player_profile"
    assert len(calls) == 2

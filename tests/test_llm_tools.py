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


def test_tool_context_ignores_client_admin():
    from nonebot_plugin_pokemon.llm.tools import resolve_context

    ctx = resolve_context(
        {
            "user_id": "u1",
            "user_name": "Tester",
            "is_admin": True,
            "platform": "evil",
            "role": "member",
        }
    )
    assert ctx.user_id == "u1"
    assert ctx.is_admin is False
    assert ctx.role == "member"
    assert ctx.platform == "web"


async def test_tool_requires_trusted_identity(uid):
    from nonebot_plugin_pokemon.llm.tools import resolve_context

    out = await execute_tool("pokemon_player_profile", {}, ToolContextData())
    assert "身份" in out.text

    out = await execute_tool("pokemon_command", {"command": "刷新每日大量出现"}, ToolContextData())
    assert "身份" in out.text

    forged = resolve_context({"user_id": uid, "is_admin": True, "role": "member"})
    out = await execute_tool("pokemon_command", {"command": "刷新每日大量出现"}, forged)
    assert "权限" in out.text or "管理员" in out.text


async def test_tool_admin_from_role(uid):
    out = await execute_tool(
        "pokemon_command",
        {"command": "刷新每日大量出现"},
        ToolContextData(user_id=uid, role="admin"),
    )
    assert "权限" not in out.text and "管理员" not in out.text

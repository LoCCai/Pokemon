from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import pytest

from nonebot_plugin_pokemon.llm import integration


class _FakeToolEffect:
    READ_ONLY = "read_only"
    MUTATING = "mutating"


class _FakeToolResult:
    def __init__(self, text="", images=(), structured=None, metadata=None):
        self.text = text
        self.images = images
        self.structured = structured
        self.metadata = metadata


class _FakeToolSpec:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class _FakeRegistry:
    def __init__(self):
        self.specs = {}

    def get(self, name):
        return self.specs.get(name)

    def unregister(self, name):
        self.specs.pop(name, None)


@pytest.fixture()
def fake_moellm(monkeypatch):
    registry = _FakeRegistry()

    def register_tool(spec):
        registry.specs[spec.name] = spec

    package = ModuleType("nonebot_plugin_moellmchats")
    package.ToolEffect = _FakeToolEffect
    package.ToolResult = _FakeToolResult
    package.ToolSpec = _FakeToolSpec
    package.register_tool = register_tool
    contracts = ModuleType("nonebot_plugin_moellmchats.tool_contracts")
    contracts.tool_registry = registry
    package.tool_contracts = contracts
    monkeypatch.setitem(sys.modules, "nonebot_plugin_moellmchats", package)
    monkeypatch.setitem(sys.modules, "nonebot_plugin_moellmchats.tool_contracts", contracts)
    monkeypatch.setattr(integration, "_REGISTERED", False)
    return registry


async def test_register_tools_with_moellm(fake_moellm, uid):
    from nonebot_plugin_pokemon.game.runner import run_command

    await run_command("领取初始精灵 小火龙", user_id=uid)
    assert integration.register() is True
    assert len(fake_moellm.specs) == 13
    assert "pokemon_player_profile" in fake_moellm.specs
    spec = fake_moellm.specs["pokemon_command"]
    assert spec.effect == "mutating"
    assert spec.permission == "user"

    handler = fake_moellm.specs["pokemon_player_profile"].handler
    context = SimpleNamespace(user_id=uid, group_id=None, user_name="Tester", is_admin=False, platform="web")
    result = await handler(_tool_context=context)
    assert "金币" in result.text
    assert result.structured["pokemon_count"] == 1

    # 幂等：第二次注册直接返回 True，不重复注册
    assert integration.register() is True
    assert len(fake_moellm.specs) == 13


async def test_mutating_tool_via_moellm(fake_moellm, uid):
    integration.register()
    handler = fake_moellm.specs["pokemon_command"].handler
    context = SimpleNamespace(user_id=uid, group_id=None, user_name="Tester", is_admin=False, platform="web")
    result = await handler(command="领取初始精灵 小火龙", _tool_context=context)
    assert "恭喜" in result.text

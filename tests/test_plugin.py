from __future__ import annotations

import nonebot


def test_plugin_registered_matcher():
    plugin = nonebot.get_plugin("nonebot_plugin_pokemon")
    assert plugin is not None
    assert plugin.metadata is not None
    assert plugin.metadata.name == "宝可梦"
    assert plugin.metadata.extra["menu_data"]
    assert len(plugin.matcher) == 1
    matcher = next(iter(plugin.matcher))
    assert matcher.block is True
    assert matcher.priority == 1
    assert matcher.handlers

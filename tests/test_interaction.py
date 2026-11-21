from __future__ import annotations

import asyncio

from nonebot_plugin_pokemon.compat.bot import Bot
from nonebot_plugin_pokemon.compat.message_models import Button
from nonebot_plugin_pokemon.game.runner import make_web_event
from nonebot_plugin_pokemon.platform.interaction import broker
from nonebot_plugin_pokemon.platform.transport import WebTransport


async def test_receive_resp_round_trip():
    ev = make_web_event("开始", user_id="interaction-u")
    transport = WebTransport(user_id="interaction-u")
    bot = Bot(ev, transport, default_timeout=3)
    task = asyncio.create_task(
        bot.receive_resp("请选择操作", [Button("野外探索", "野外探索", "野外探索", action=2)], timeout=3)
    )
    await asyncio.sleep(0.1)
    assert broker.has_waiter(ev.scene_key)
    reply = make_web_event("野外探索", user_id="interaction-u")
    assert broker.feed(reply)
    result = await asyncio.wait_for(task, 2)
    assert result is not None
    assert result.text == "野外探索"
    assert transport.outbox
    assert transport.outbox[0].buttons
    assert not broker.has_waiter(ev.scene_key)


async def test_receive_resp_timeout():
    ev = make_web_event("开始", user_id="interaction-timeout-u")
    bot = Bot(ev, WebTransport(user_id="interaction-timeout-u"), default_timeout=0.1)
    result = await bot.receive_resp("请选择", timeout=0.1)
    assert result is None
    assert not broker.has_waiter(ev.scene_key)

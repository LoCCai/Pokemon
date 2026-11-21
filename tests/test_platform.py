from __future__ import annotations

import asyncio

import pytest

from nonebot_plugin_pokemon.compat.models import Event
from nonebot_plugin_pokemon.platform.interaction import InteractionBroker
from nonebot_plugin_pokemon.resources.downloader import parse_index


def _event(key="u1", text="1"):
    return Event(
        bot_id="web",
        bot_self_id="web",
        user_type="direct",
        user_id=key,
        raw_text=text,
        platform="web",
    )


async def test_broker_feed():
    broker = InteractionBroker()
    queue = broker.register("web:web:direct:-:u1")
    ev = _event()
    assert broker.feed(ev)
    received = await asyncio.wait_for(queue.get(), 1)
    assert received.text == "1"


async def test_broker_no_waiter():
    broker = InteractionBroker()
    assert not broker.feed(_event())


async def test_broker_isolates_group_members():
    broker = InteractionBroker()
    broker.register("onebot11:10000:group:30000:u1")
    other = Event(
        bot_id="10000",
        bot_self_id="10000",
        user_type="group",
        group_id="30000",
        user_id="u2",
        raw_text="1",
        platform="onebot11",
    )
    assert not broker.feed(other)


async def test_broker_persistent():
    broker = InteractionBroker()
    broker.attach("web:web:direct:-:u1")
    broker.unregister("web:web:direct:-:u1")
    assert broker.has_waiter("web:web:direct:-:u1")
    broker.detach("web:web:direct:-:u1")
    assert not broker.has_waiter("web:web:direct:-:u1")


def test_parse_index():
    html = (
        '<pre><a href="../">../</a>\n'
        '<a href="%E7%9A%AE%E5%8D%A1%E4%B8%98.png">皮卡丘.png</a>  22-Nov-2023 07:33  83293\n'
        '<a href="小火龙.png">小火龙.png</a>  22-Nov-2023 07:33  12345\n'
        "</pre>"
    )
    entries = parse_index(html)
    assert ("皮卡丘.png", 83293) in entries
    assert ("小火龙.png", 12345) in entries


def test_placeholder_image(tmp_path):
    from nonebot_plugin_pokemon.compat.media import open_image

    image = open_image(tmp_path / "missing.png", size=(64, 64))
    assert image.size == (64, 64)

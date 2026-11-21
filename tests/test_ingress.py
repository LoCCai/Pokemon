from __future__ import annotations

from types import SimpleNamespace

from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.adapters.onebot.v12.event import MessageEvent as V12MessageEvent
from nonebot.adapters.qq.event import GroupAtMessageCreateEvent

from nonebot_plugin_pokemon.platform.ingress import adapter_kind, clean_text, to_event


class FakeBot:
    self_id = "10000"


def _real_v11_event():
    return GroupMessageEvent.model_validate(
        {
            "time": 1700000000,
            "self_id": 10000,
            "post_type": "message",
            "message_type": "group",
            "sub_type": "normal",
            "message_id": 1,
            "user_id": 20000,
            "group_id": 30000,
            "message": [
                {"type": "at", "data": {"qq": "10000"}},
                {"type": "text", "data": {"text": " 精灵图鉴 皮卡丘"}},
            ],
            "raw_message": "",
            "font": 0,
            "sender": {"user_id": 20000, "nickname": "Tester", "card": "", "role": "admin"},
            "anonymous": None,
            "original_message": [],
        }
    )


def test_onebot11_event():
    ev = to_event(FakeBot(), _real_v11_event())
    assert ev is not None
    assert ev.platform == "onebot11"
    assert (ev.user_id, ev.group_id) == ("20000", "30000")
    assert ev.raw_text == "精灵图鉴 皮卡丘"
    assert ev.is_tome and ev.at_bot
    assert ev.sender["nickname"] == "Tester"
    assert ev.user_pm == 3


class _FakeMessage:
    def __init__(self, segments):
        self._segments = segments

    def __iter__(self):
        return iter(self._segments)


class FakeV12Event:
    detail_type = "group"
    group_id = "g-1"
    user_id = "u-1"
    message_id = "m-1"
    sender = {"nickname": "V12"}
    to_me = True

    def get_message(self):
        return _FakeMessage([SimpleNamespace(type="mention", data={"user_id": "10000"})])

    def get_plaintext(self):
        return "野外探索"


FakeV12Event.__module__ = "nonebot.adapters.onebot.v12.event"


def test_onebot12_event():
    ev = to_event(FakeBot(), FakeV12Event())
    assert ev is not None
    assert ev.platform == "onebot12"
    assert ev.user_type == "group"
    assert ev.group_id == "g-1"
    assert ev.raw_text == "野外探索"
    assert ev.is_tome
    assert adapter_kind(FakeBot(), FakeV12Event()) == "onebot12"


class FakeQQEvent:
    group_openid = "qq-group"
    id = "qq-msg"
    to_me = True
    author = SimpleNamespace(member_openid="qq-user", nickname="QQ玩家")

    def get_user_id(self):
        return "qq-user"

    def get_plaintext(self):
        return "宝可梦帮助"


FakeQQEvent.__module__ = "nonebot.adapters.qq.event"


def test_qq_event():
    ev = to_event(FakeBot(), FakeQQEvent())
    assert ev is not None
    assert ev.platform == "qq"
    assert ev.user_type == "group"
    assert ev.group_id == "qq-group"
    assert ev.raw_text == "宝可梦帮助"
    assert ev.is_tome
    assert adapter_kind(FakeBot(), FakeQQEvent()) == "qq"


def test_clean_text_variants():
    assert clean_text("/领取初始精灵 小火龙") == "领取初始精灵 小火龙"
    assert clean_text("  /  /野外探索") == "/野外探索"
    assert clean_text("<@!10000>  /精灵状态皮卡丘") == "精灵状态皮卡丘"
    assert clean_text("\u3000\u3000") == ""


def test_real_onebot12_event():
    event = V12MessageEvent.model_validate(
        {
            "id": "evt-1",
            "time": 1700000000,
            "type": "message",
            "detail_type": "group",
            "sub_type": "normal",
            "self": {"platform": "qq", "user_id": "10000"},
            "message_id": "m1",
            "message": [{"type": "text", "data": {"text": "/宝可梦帮助"}}],
            "alt_message": "/宝可梦帮助",
            "user_id": "20000",
            "group_id": "30000",
            "sender": {"user_id": "20000", "nickname": "V12", "role": "member"},
        }
    )
    ev = to_event(FakeBot(), event)
    assert ev is not None
    assert ev.platform == "onebot12"
    assert ev.raw_text == "宝可梦帮助"
    assert (ev.user_id, ev.group_id) == ("20000", "30000")


def test_real_qq_group_event():
    event = GroupAtMessageCreateEvent.model_validate(
        {
            "id": "m1",
            "content": " /宝可梦帮助",
            "timestamp": "2026-01-01T00:00:00+08:00",
            "author": {
                "id": "1",
                "bot": False,
                "member_openid": "qq-user",
                "member_role": "member",
                "username": "QQ玩家",
            },
            "group_openid": "qq-group",
            "group_id": "qq-group",
        }
    )
    ev = to_event(FakeBot(), event)
    assert ev is not None
    assert ev.platform == "qq"
    assert ev.raw_text == "宝可梦帮助"
    assert ev.group_id == "qq-group"
    assert ev.is_tome

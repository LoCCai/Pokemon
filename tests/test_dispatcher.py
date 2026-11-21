from __future__ import annotations

from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message

from nonebot_plugin_pokemon.game.runner import run_command
from nonebot_plugin_pokemon.matchers.dispatcher import _handle, _rule


def _event(user_id: str, text: str) -> GroupMessageEvent:
    return GroupMessageEvent.model_validate(
        {
            "time": 1700000000,
            "self_id": 10000,
            "post_type": "message",
            "message_type": "group",
            "sub_type": "normal",
            "message_id": 1,
            "user_id": int(user_id) if user_id.isdigit() else 20000,
            "group_id": 30000,
            "message": [{"type": "text", "data": {"text": text}}],
            "raw_message": "",
            "font": 0,
            "sender": {"user_id": 20000, "nickname": "Tester", "card": "", "role": "member"},
            "anonymous": None,
            "original_message": [],
        }
    )


class CaptureBot:
    self_id = "10000"

    def __init__(self):
        self.messages = []

    async def send(self, event, message):
        self.messages.append(message)
        return None


def _text(message) -> str:
    if isinstance(message, str):
        return message
    return "".join(seg.data.get("text", "") for seg in message if seg.type == "text")


async def test_dispatcher_handles_real_v11_event():
    uid = "30001"
    await run_command("领取初始精灵 小火龙", user_id=uid)
    bot = CaptureBot()
    event = _event(uid, "野外探索")
    assert _rule(bot, event)
    await _handle(bot, event, {})
    assert bot.messages
    assert _text(bot.messages[0])


async def test_dispatcher_ignores_non_game_text():
    bot = CaptureBot()
    assert not _rule(bot, _event("30002", "今天天气不错"))


async def test_dispatcher_denies_admin_command():
    bot = CaptureBot()
    event = _event("30003", "刷新每日大量出现")
    assert _rule(bot, event)
    await _handle(bot, event, {})
    assert bot.messages
    assert "权限" in _text(bot.messages[0])

"""入站事件归一化：OneBot v11 / OneBot v12 / QQ 官方机器人 -> compat.Event。"""

from __future__ import annotations

import re
from typing import Any, Optional

from ..compat.models import Event

_AT_TAG_RE = re.compile(r"<@!?[^>]+>")


def adapter_kind(bot: Any, event: Any) -> str:
    module = type(event).__module__
    if "onebot.v11" in module:
        return "onebot11"
    if "onebot.v12" in module:
        return "onebot12"
    if "adapters.qq" in module:
        return "qq"
    return "unknown"


def adapter_kind_of_bot(bot: Any) -> str:
    module = type(bot).__module__
    if "onebot.v11" in module:
        return "onebot11"
    if "onebot.v12" in module:
        return "onebot12"
    if "adapters.qq" in module:
        return "qq"
    return "unknown"


def command_starts() -> set[str]:
    starts: set[str] = set()
    try:
        from nonebot import get_driver

        starts.update(s for s in get_driver().config.command_start if s)
    except Exception:
        starts.add("/")
    try:
        from ..config import plugin_config

        starts.update(s for s in plugin_config.pokemon_command_prefixes if s)
    except Exception:
        pass
    return starts


def clean_text(text: str) -> str:
    """去掉 @ 标签、首尾空白，以及 NoneBot 的命令起始符。"""

    text = _AT_TAG_RE.sub("", text or "")
    text = text.replace("\r\n", "\n").replace("\u200b", "").strip()
    # 官方机器人在部分场景会在正文前加空格或全角空格
    text = text.lstrip(" \t\u3000\u00a0")
    starts = command_starts()
    if text and text[0] in starts:
        text = text[1:].lstrip(" \t\u3000\u00a0")
    return text


def _sender_dict(raw: Any) -> dict:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    result: dict[str, Any] = {}
    for key in ("nickname", "card", "role", "user_id", "member_openid", "username"):
        value = getattr(raw, key, None)
        if value is not None:
            result[key] = value
    return result


def _role_pm(role: str) -> int:
    role = (role or "").lower()
    if role in {"owner"}:
        return 2
    if role in {"admin", "administrator"}:
        return 3
    return 6


def to_event(bot: Any, nb_event: Any) -> Optional[Event]:
    kind = adapter_kind(bot, nb_event)
    if kind == "onebot11":
        return _from_onebot11(bot, nb_event)
    if kind == "onebot12":
        return _from_onebot12(bot, nb_event)
    if kind == "qq":
        return _from_qq(bot, nb_event)
    return None


def _from_onebot11(bot: Any, nb_event: Any) -> Event:
    self_id = str(getattr(bot, "self_id", "") or "")
    group_id = getattr(nb_event, "group_id", None)
    user_id = str(getattr(nb_event, "user_id", "") or "")
    message = nb_event.get_message()
    at_list = []
    at_bot = False
    for seg in message:
        if seg.type == "at":
            uid = str(seg.data.get("qq", ""))
            if uid == self_id:
                at_bot = True
            elif uid:
                at_list.append(uid)
    text = clean_text(nb_event.get_plaintext())
    sender = _sender_dict(getattr(nb_event, "sender", None))
    role = str(sender.get("role", "") or "")
    try:
        is_tome = bool(nb_event.is_tome())
    except Exception:
        is_tome = False
    return Event(
        bot_id=self_id or "onebot11",
        bot_self_id=self_id,
        msg_id=str(getattr(nb_event, "message_id", "") or ""),
        user_type="group" if group_id else "direct",
        group_id=str(group_id) if group_id else None,
        user_id=user_id,
        sender=sender,
        user_pm=_role_pm(role),
        raw_text=text,
        at=at_list[0] if at_list else None,
        at_list=at_list,
        is_tome=is_tome or at_bot,
        at_bot=at_bot,
        raw_event=nb_event,
        platform="onebot11",
        transport=None,
    )


def _from_onebot12(bot: Any, nb_event: Any) -> Event:
    self_id = str(getattr(bot, "self_id", "") or "")
    detail_type = str(getattr(nb_event, "detail_type", "") or "")
    group_id = getattr(nb_event, "group_id", None) or getattr(nb_event, "channel_id", None)
    user_id = str(getattr(nb_event, "user_id", "") or "")
    at_list = []
    at_bot = False
    for seg in nb_event.get_message():
        if seg.type in {"mention", "at"}:
            uid = str(seg.data.get("user_id") or seg.data.get("qq") or "")
            if uid == self_id:
                at_bot = True
            elif uid:
                at_list.append(uid)
    text = clean_text(nb_event.get_plaintext())
    sender = _sender_dict(getattr(nb_event, "sender", None))
    role = str(sender.get("role", "") or "")
    return Event(
        bot_id=self_id or "onebot12",
        bot_self_id=self_id,
        msg_id=str(getattr(nb_event, "message_id", "") or ""),
        user_type="direct" if detail_type in {"private", "direct"} else ("channel" if detail_type == "channel" else "group"),
        group_id=str(group_id) if group_id else None,
        user_id=user_id,
        sender=sender,
        user_pm=_role_pm(role),
        raw_text=text,
        at=at_list[0] if at_list else None,
        at_list=at_list,
        is_tome=bool(getattr(nb_event, "to_me", False)) or at_bot,
        at_bot=at_bot,
        raw_event=nb_event,
        platform="onebot12",
        transport=None,
    )


def _from_qq(bot: Any, nb_event: Any) -> Event:
    self_id = str(getattr(bot, "self_id", "") or "")
    class_name = type(nb_event).__name__
    group_id = getattr(nb_event, "group_openid", None) or getattr(nb_event, "group_id", None)
    channel_id = getattr(nb_event, "channel_id", None)
    if "C2C" in class_name:
        user_type = "direct"
        group_id = None
    elif channel_id:
        user_type = "channel"
        group_id = str(channel_id)
    else:
        user_type = "group"
    user_id = str(nb_event.get_user_id())
    text = clean_text(nb_event.get_plaintext())
    author = getattr(nb_event, "author", None)
    sender = _sender_dict(author)
    return Event(
        bot_id=self_id or "qq",
        bot_self_id=self_id,
        msg_id=str(getattr(nb_event, "id", "") or ""),
        user_type=user_type,
        group_id=str(group_id) if group_id else None,
        user_id=user_id,
        sender=sender,
        user_pm=6,
        raw_text=text,
        at=None,
        at_list=[],
        is_tome=bool(getattr(nb_event, "to_me", False)),
        at_bot=bool(getattr(nb_event, "to_me", False)),
        raw_event=nb_event,
        platform="qq",
        transport=None,
    )


__all__ = ["adapter_kind", "adapter_kind_of_bot", "clean_text", "command_starts", "to_event"]

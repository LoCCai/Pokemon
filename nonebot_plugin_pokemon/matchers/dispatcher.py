"""统一分发 Matcher：把 NoneBot2 事件路由到 gsuid 风格的游戏处理器。"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from nonebot import get_driver, on_message
from nonebot.adapters import Bot as NBOT, Event as NEVENT
from nonebot.matcher import Matcher
from nonebot.typing import T_State

from ..compat.bot import Bot
from ..compat.logger import logger
from ..compat.models import Event
from ..compat.sv import SV, Trigger
from ..platform.ingress import adapter_kind, to_event
from ..platform.interaction import broker
from ..platform.sender import register_proactive
from ..platform.transport import AdapterTransport

ADMIN_DENIED = "该指令需要管理员权限，请联系超级管理员或群管理员。"
_SKIP_KEY = "_pokemon_skip"


def _is_superuser(user_id: str) -> bool:
    try:
        return str(user_id) in {str(x) for x in get_driver().config.superusers}
    except Exception:
        return False


def _permission_ok(ev: Event, trigger: Trigger) -> bool:
    pm = trigger.sv.pm
    if _is_superuser(ev.user_id):
        return True
    if pm >= 6:
        return True
    role = str(ev.sender.get("role", "") or "").lower()
    owner = role == "owner"
    admin = owner or role in {"admin", "administrator"}
    if pm == 0:
        return False
    if pm == 1:
        return False
    if pm == 2:
        return owner
    if pm == 3:
        return admin
    return False


def _rule(bot: NBOT, event: NEVENT) -> bool:
    try:
        ev = to_event(bot, event)
    except Exception:
        return False
    if ev is None:
        return False
    if not ev.raw_text:
        return False
    if broker.has_waiter(ev.scene_key):
        return True
    return SV.find(ev.raw_text) is not None


async def _handle(bot: NBOT, event: NEVENT, state: T_State) -> None:
    kind = adapter_kind(bot, event)
    ev = to_event(bot, event)
    if ev is None:
        return
    register_proactive(bot, kind)
    ev.transport = AdapterTransport(bot, event, kind)

    # 优先投递到战斗/小游戏等待队列
    if broker.feed(ev):
        return

    found = SV.find(ev.raw_text)
    if found is None:
        return
    trigger, arg = found
    if trigger.to_me and not ev.is_tome:
        return
    if not _permission_ok(ev, trigger):
        await bot.send(event, ADMIN_DENIED)
        return

    ev.command = trigger.keyword
    ev.text = arg
    compat_bot = Bot(ev, ev.transport)
    try:
        result = trigger.func(compat_bot, ev)
        if asyncio.iscoroutine(result):
            await result
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # 单条指令失败不应拖垮 Bot
        logger.exception(f"[pokemon] 指令 {trigger.keyword} 执行失败: {exc}")
        try:
            await bot.send(event, f"指令执行失败：{type(exc).__name__}")
        except Exception:
            pass
    finally:
        compat_bot.release_interactions()


def register_matcher() -> Matcher:
    return on_message(priority=1, block=True, rule=_rule, handlers=[_handle])


__all__ = ["register_matcher"]

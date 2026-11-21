"""指令执行器：把一条网页/LLM 指令跑过游戏处理器并收集出站消息。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..compat.bot import Bot
from ..compat.logger import logger
from ..compat.models import Event
from ..compat.sv import SV
from ..identity import effective_role, event_is_admin, event_role, is_admin_role
from ..platform.ingress import clean_text
from ..platform.interaction import broker
from ..platform.message import OutMessage
from ..platform.transport import WebTransport


def _buttons(messages: List[OutMessage]) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for message in messages:
        for button in message.buttons:
            data = button.data or button.text
            if data in seen:
                continue
            seen.add(data)
            result.append(
                {
                    "text": button.text,
                    "data": data,
                    "pressed_text": button.pressed_text,
                    "action": button.action,
                }
            )
    return result


@dataclass
class RunResult:
    ok: bool = True
    matched: bool = False
    denied: bool = False
    command: str = ""
    text: str = ""
    images: List[str] = field(default_factory=list)
    buttons: List[Dict[str, Any]] = field(default_factory=list)
    messages: List[Dict[str, Any]] = field(default_factory=list)
    awaiting: bool = False
    interactive: bool = False
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "matched": self.matched,
            "denied": self.denied,
            "command": self.command,
            "text": self.text,
            "images": self.images,
            "buttons": self.buttons,
            "messages": self.messages,
            "awaiting": self.awaiting,
            "interactive": self.interactive,
            "error": self.error,
        }


def _messages(outbox: List[OutMessage]) -> List[Dict[str, Any]]:
    from .charts import to_data_url

    result = []
    for message in outbox:
        items = []
        text_parts = []
        for seg in message.segments:
            if seg.type == "image" and isinstance(seg.data, (bytes, bytearray)):
                items.append({"type": "image", "data": to_data_url(bytes(seg.data))})
            elif seg.type == "buttons":
                continue
            else:
                items.append(seg.to_dict())
                if seg.type == "text":
                    text_parts.append(str(seg.data))
        result.append({"segments": items, "text": "".join(text_parts)})
    return result


def _is_admin(ev: Event) -> bool:
    """网页/宿主事件只按可信角色判定管理员。

    聊天平台仍允许 NoneBot ``SUPERUSERS`` 兜底；但网页身份由宿主
    ``account.role`` 决定，不能让一个 QQ 恰好等于 SUPERUSERS 就获得管理权。
    """

    if ev.platform in {"web", "qweb"}:
        return event_is_admin(ev)
    if ev.user_pm <= 1:
        return True
    if is_admin_role(event_role(ev)):
        return True
    try:
        from nonebot import get_driver

        return str(ev.user_id) in {str(x) for x in get_driver().config.superusers}
    except Exception:
        return False


def _permission_ok(ev: Event, pm: int) -> bool:
    if _is_admin(ev):
        return True
    if pm >= 6:
        return True
    role = event_role(ev)
    if pm == 2:
        return role == "owner"
    if pm == 3:
        return is_admin_role(role)
    return False


def make_web_event(
    text: str,
    *,
    user_id: str,
    group_id: Optional[str] = None,
    user_name: str = "网页玩家",
    is_admin: bool = False,
    role: str = "",
    platform: str = "web",
    session_suffix: str = "",
) -> Event:
    trusted_role = effective_role(role, is_admin=is_admin)
    admin = is_admin_role(trusted_role)
    session_id = f"web:{user_id}{session_suffix}"
    if group_id:
        # 只有聊天侧可信上下文才会带群；QWeb 路由固定不传群。
        session_id = f"web:group:{group_id}:{user_id}{session_suffix}"
    return Event(
        bot_id="web",
        bot_self_id="web",
        user_type="group" if group_id else "direct",
        group_id=str(group_id) if group_id else None,
        user_id=str(user_id),
        sender={"nickname": user_name, "role": trusted_role},
        user_pm=1 if admin else 6,
        raw_text=clean_text(text),
        platform=platform,
        session_id=session_id,
    )


async def run_command(
    text: str,
    *,
    user_id: str,
    group_id: Optional[str] = None,
    user_name: str = "网页玩家",
    is_admin: bool = False,
    role: str = "",
    timeout: float = 20.0,
    interaction_timeout: float = 6.0,
) -> RunResult:
    trusted_role = effective_role(role, is_admin=is_admin)
    admin = is_admin_role(trusted_role)
    ev = make_web_event(
        text,
        user_id=user_id,
        group_id=group_id,
        user_name=user_name,
        is_admin=admin,
        role=trusted_role,
    )
    result = RunResult(command=clean_text(text))
    if not ev.raw_text:
        result.ok = False
        result.error = "指令为空"
        return result

    found = SV.find(ev.raw_text)
    if found is None:
        result.ok = False
        result.error = "没有匹配的宝可梦指令"
        return result

    trigger, arg = found
    result.matched = True
    result.interactive = "receive_" in _source(trigger.func)
    if not _permission_ok(ev, trigger.sv.pm):
        result.denied = True
        result.ok = False
        result.error = "该指令需要管理员权限"
        return result

    ev.command = trigger.keyword
    ev.text = arg
    transport = WebTransport(user_id=str(user_id), user_name=user_name, is_admin=admin)
    ev.transport = transport
    bot = Bot(ev, transport, default_timeout=interaction_timeout)

    async def _run() -> None:
        res = trigger.func(bot, ev)
        if asyncio.iscoroutine(res):
            await res

    task = asyncio.create_task(_run())
    try:
        await asyncio.wait_for(asyncio.shield(task), timeout=timeout)
    except asyncio.TimeoutError:
        result.awaiting = True
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.exception(f"[pokemon] 网页指令 {trigger.keyword} 执行失败: {exc}")
        result.ok = False
        result.error = f"{type(exc).__name__}: {exc}"
    finally:
        if not task.done():
            task.cancel()
            try:
                await task
            except Exception:
                pass
        bot.release_interactions()

    result.text = "\n".join(r.text for r in transport.results if r.text)
    result.images = [m["data"] for msg in _messages(transport.outbox) for m in msg["segments"] if m["type"] == "image"]
    result.buttons = _buttons(transport.outbox)
    result.messages = _messages(transport.outbox)
    if not result.ok and not result.error:
        result.error = "未产生回复"
    return result


def _source(func: Any) -> str:
    try:
        import inspect

        return inspect.getsource(func)
    except Exception:
        return ""


async def run_and_format(text: str, **kwargs: Any) -> str:
    """给 LLM 工具用的紧凑文本结果。"""

    result = await run_command(text, **kwargs)
    if result.denied:
        return "该指令需要管理员权限。"
    if not result.matched:
        return f"没有匹配 `{text}` 的宝可梦指令。"
    parts = []
    if result.text:
        parts.append(result.text)
    if result.images:
        parts.append(f"[生成了 {len(result.images)} 张图片]")
    if result.buttons:
        parts.append("可选操作：" + " / ".join(b["data"] for b in result.buttons[:12]))
    if result.awaiting:
        parts.append("该指令进入连续交互（战斗/小游戏），请提示用户在网页或聊天中继续操作。")
    if result.error and result.ok:
        parts.append(f"错误：{result.error}")
    return "\n".join(parts) or "指令已执行，但没有文本输出。"


__all__ = ["RunResult", "make_web_event", "run_and_format", "run_command"]

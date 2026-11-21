"""网页游戏会话：支持战斗/小游戏等连续交互。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..compat.bot import Bot
from ..compat.logger import logger
from ..compat.sv import SV
from ..platform.interaction import broker
from ..platform.message import OutMessage
from ..platform.transport import WebTransport
from ..game.runner import _buttons, _messages, _permission_ok, make_web_event


@dataclass
class _Session:
    user_id: str
    group_id: Optional[str] = None
    user_name: str = "网页玩家"
    is_admin: bool = False
    transport: WebTransport = field(default_factory=WebTransport)
    event: Any = None
    bot: Any = None
    task: Optional[asyncio.Task] = None
    error: str = ""
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    cursor: int = 0

    @property
    def key(self) -> str:
        return f"{self.user_id}:{self.group_id or ''}"


class WebSessionRegistry:
    def __init__(self) -> None:
        self._sessions: Dict[str, _Session] = {}

    def get(
        self,
        user_id: str,
        group_id: Optional[str] = None,
        user_name: str = "网页玩家",
        is_admin: bool = False,
    ) -> _Session:
        key = f"{user_id}:{group_id or ''}"
        session = self._sessions.get(key)
        if session is None:
            session = _Session(
                user_id=str(user_id),
                group_id=str(group_id) if group_id else None,
                user_name=user_name,
                is_admin=is_admin,
            )
            self._sessions[key] = session
        else:
            session.user_name = user_name
            session.is_admin = is_admin
        return session

    async def submit(
        self,
        session: _Session,
        text: str,
    ) -> Dict[str, Any]:
        async with session.lock:
            if session.task is not None and not session.task.done():
                if broker.has_waiter(session.event.scene_key):
                    return await self._feed(session, text)
                return self._snapshot(session, error="上一条指令仍在执行，请稍候。")

            result = self._start(session, text)
            if result is not None:
                return result
            await self._short_wait(session)
            return self._snapshot(session)

    def _start(self, session: _Session, text: str) -> Optional[Dict[str, Any]]:
        ev = make_web_event(
            text,
            user_id=session.user_id,
            group_id=session.group_id,
            user_name=session.user_name,
            is_admin=session.is_admin,
        )
        if not ev.raw_text:
            return self._snapshot(session, error="请输入指令。")
        found = SV.find(ev.raw_text)
        if found is None:
            return self._snapshot(session, error=f"没有匹配的宝可梦指令：{ev.raw_text}")
        trigger, arg = found
        if not _permission_ok(ev, trigger.sv.pm):
            return self._snapshot(session, error="该指令需要管理员权限。")

        ev.command = trigger.keyword
        ev.text = arg
        session.transport = WebTransport(
            user_id=session.user_id,
            user_name=session.user_name,
            is_admin=session.is_admin,
        )
        ev.transport = session.transport
        session.event = ev
        session.bot = Bot(ev, session.transport)
        session.error = ""

        async def _run() -> None:
            try:
                res = trigger.func(session.bot, ev)
                if asyncio.iscoroutine(res):
                    await res
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception(f"[pokemon] 网页会话指令 {trigger.keyword} 失败: {exc}")
                session.error = f"{type(exc).__name__}: {exc}"
            finally:
                session.bot.release_interactions()

        session.task = asyncio.create_task(_run(), name=f"pokemon-web-{session.key}")
        return None

    async def _feed(self, session: _Session, text: str) -> Dict[str, Any]:
        ev = make_web_event(
            text,
            user_id=session.user_id,
            group_id=session.group_id,
            user_name=session.user_name,
            is_admin=session.is_admin,
        )
        if not ev.raw_text:
            return self._snapshot(session, error="请输入内容。")
        before = len(session.transport.outbox)
        broker.feed(ev)
        await self._wait_output(session, before, timeout=3.0)
        return self._snapshot(session)

    async def _short_wait(self, session: _Session, timeout: float = 0.8) -> None:
        before = len(session.transport.outbox)
        await self._wait_output(session, before, timeout)

    async def _wait_output(self, session: _Session, before: int, timeout: float) -> None:
        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            if len(session.transport.outbox) > before:
                return
            if session.task is not None and session.task.done():
                return
            await asyncio.sleep(0.05)

    def _snapshot(self, session: _Session, error: str = "") -> Dict[str, Any]:
        outbox = list(session.transport.outbox)
        messages = _messages(outbox)
        tools = _buttons(outbox)
        awaiting = bool(session.event is not None and broker.has_waiter(session.event.scene_key))
        done = session.task is None or session.task.done()
        return {
            "ok": not (error or session.error),
            "error": error or session.error,
            "messages": messages,
            "buttons": tools,
            "awaiting": awaiting,
            "done": done,
            "text": "\n".join(m.get("text", "") for m in messages if m.get("text")),
            "images": [
                seg["data"]
                for msg in messages
                for seg in msg.get("segments", [])
                if seg.get("type") == "image"
            ],
        }

    async def cancel(self, session: _Session) -> None:
        async with session.lock:
            if session.task is not None and not session.task.done():
                session.task.cancel()
                try:
                    await session.task
                except Exception:
                    pass
            if session.bot is not None:
                session.bot.release_interactions()
            session.error = "已取消当前连续交互。"


registry = WebSessionRegistry()

__all__ = ["WebSessionRegistry", "registry"]

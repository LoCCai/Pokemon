"""网页游戏会话：支持战斗/小游戏等连续交互。

会话状态只由可信身份决定：

* key 使用宿主 ``account.qq``（+ 可信群，若有），不读取客户端声明的群；
* 角色在创建/复用会话时更新，并传给每一条后续交互事件；
* 管理员标记始终由角色推导，不能在第二次请求里用 ``is_admin`` 改写。

新增的 ``act`` 是 QWeb 原生游戏动作入口：只接受 allow-list 动作，在会话锁内
校验 operation/offset 并调用真实游戏处理器，旧 operation 在动作完成后立即
失效，因此过期/replay 的回合会被拒绝。
"""

from __future__ import annotations

import asyncio
from uuid import uuid4
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from ..game.web_turn import turn_bot
from ..compat.bot import Bot
from ..compat.logger import logger
from ..compat.sv import SV
from ..identity import effective_role, is_admin_role
from ..platform.interaction import broker
from ..platform.message import OutMessage
from ..platform.projection import accepted_reply_values, build_state, extract_options
from ..platform.transport import WebTransport
from ..game.actions import ALLOWED_ACTIONS, ActionError, owned_ids, resolve_action
from ..game.runner import _buttons, _messages, _permission_ok, make_web_event


@dataclass
class _Session:
    user_id: str
    group_id: Optional[str] = None
    user_name: str = "网页玩家"
    role: str = "member"
    transport: WebTransport = field(default_factory=WebTransport)
    event: Any = None
    bot: Any = None
    task: Optional[asyncio.Task] = None
    error: str = ""
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    operation: str = ""
    turn: int = 0
    last_action: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_admin(self) -> bool:
        return is_admin_role(self.role)

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
        role: str = "",
    ) -> _Session:
        role = effective_role(role, is_admin=is_admin)
        key = f"{user_id}:{group_id or ''}"
        session = self._sessions.get(key)
        if session is None:
            session = _Session(
                user_id=str(user_id),
                group_id=str(group_id) if group_id else None,
                user_name=user_name,
                role=role,
            )
            self._sessions[key] = session
        else:
            session.user_name = user_name
            # 角色以本次可信身份为准，允许升级/降级；不再单独保存 is_admin。
            session.role = role
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

    # ------------------------------------------------------------------ actions
    async def act(
        self,
        session: _Session,
        action: str,
        value: Any = None,
        operation: str = "",
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Execute one typed QWeb gameplay action under the registry lock.

        An old ``operation`` (or a replay of a whole request body) is rejected
        with HTTP 409 semantics; each accepted turn mints a new operation token.
        """

        async with session.lock:
            if self._stale(session, operation, offset):
                return self._snapshot(
                    session,
                    error="操作已过期，请刷新当前状态后重试。",
                    offset=max(0, int(offset or 0)),
                    stale=True,
                )

            action = str(action or "").strip()
            if action not in ALLOWED_ACTIONS:
                raise ActionError("不支持的游戏操作。")

            if action == "cancel":
                await self._cancel_locked(session)
                self._advance(session, "cancel", None)
                return self._snapshot(session, canceled=True)

            if action == "reply":
                if not (session.event is not None and broker.has_waiter(session.event.scene_key)):
                    raise ActionError("当前没有等待回复的交互。", status_code=409)
                canonical = self._legal_reply(session, value)
                self._advance(session, "reply", canonical)
                before = len(session.transport.outbox)
                ev = make_web_event(
                    canonical,
                    user_id=session.user_id,
                    group_id=session.group_id,
                    user_name=session.user_name,
                    is_admin=session.is_admin,
                    role=session.role,
                )
                if not ev.raw_text:
                    raise ActionError("回复内容为空。")
                broker.feed(ev)
                await self._wait_output(session, before, timeout=3.0)
                return self._snapshot(session, offset=before)

            if session.task is not None and not session.task.done():
                if session.event is not None and broker.has_waiter(session.event.scene_key):
                    raise ActionError("当前正在等待你的选择，请先回复或取消。", status_code=409)
                return self._snapshot(session, error="上一条指令仍在执行，请稍候。")

            owned: Optional[Sequence[int]] = None
            if action in {"party", "equip"}:
                owned = await owned_ids(session.user_id)
            resolved = resolve_action(action, value, uid=session.user_id, owned=owned)
            command = str(resolved.get("command") or "")
            if not command:
                raise ActionError("该操作没有可执行的游戏处理器。")
            result = self._start(session, command, native=True)
            session.last_action = {
                "action": action,
                "value": resolved.get("value"),
            }
            if result is not None:
                return result
            await self._short_wait(session)
            return self._snapshot(session)

    def _stale(self, session: _Session, operation: str, offset: int) -> bool:
        operation = str(operation or "").strip()
        if session.operation:
            if not operation:
                # A brand new session may act without a token; once a turn exists
                # the caller must present the token from its latest snapshot.
                return bool(session.turn)
            return operation != session.operation or offset != len(session.transport.outbox)
        if operation:
            return True
        try:
            return int(offset or 0) > len(session.transport.outbox)
        except (TypeError, ValueError):
            return True

    def _legal_reply(self, session: _Session, value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            raise ActionError("回复内容为空。")
        if len(text) > 500:
            raise ActionError("回复内容过长。")
        accepted = accepted_reply_values(session.transport.outbox)
        if not accepted:
            return text
        canonical = accepted.get(text)
        if canonical is None:
            raise ActionError("请选择当前可用的操作或技能。")
        return canonical

    def _advance(self, session: _Session, action: str, value: Any) -> None:
        session.operation = uuid4().hex
        session.turn += 1
        session.last_action = {"action": action, "value": value}

    def _start(self, session: _Session, text: str, *, native: bool = False) -> Optional[Dict[str, Any]]:
        # 新指令开始前先丢弃上一条指令的出站消息和等待事件，避免把旧连续交互
        # 的输出/状态带到新指令里。
        self._advance(session, "command", text)
        session.transport = WebTransport(
            user_id=session.user_id,
            user_name=session.user_name,
            is_admin=session.is_admin,
        )
        session.event = None
        session.bot = None
        session.error = ""

        ev = self._make_event(text, session)
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
        ev.transport = session.transport
        session.event = ev
        session.bot = Bot(ev, session.transport)

        async def _run() -> None:
            context = turn_bot.set(session.bot if native else None)
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
                turn_bot.reset(context)
                session.bot.release_interactions()

        session.task = asyncio.create_task(_run(), name=f"pokemon-web-{session.key}")
        return None

    def _make_event(self, text: str, session: _Session):
        return make_web_event(
            text,
            user_id=session.user_id,
            group_id=session.group_id,
            user_name=session.user_name,
            is_admin=session.is_admin,
            role=session.role,
        )

    async def _feed(self, session: _Session, text: str) -> Dict[str, Any]:
        ev = self._make_event(text, session)
        if not ev.raw_text:
            return self._snapshot(session, error="请输入内容。")
        before = len(session.transport.outbox)
        broker.feed(ev)
        await self._wait_output(session, before, timeout=3.0)
        return self._snapshot(session, offset=before)

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

    def status(self, session: _Session, operation: str, offset: int) -> Dict[str, Any]:
        if operation and operation != session.operation:
            return {"superseded": True, "done": True, "messages": [], "state": build_state(
                session.transport.projection,
                operation=session.operation,
                turn=session.turn,
                awaiting=False,
                done=True,
                battle_view=session.transport.battle_view,
            )}
        return self._snapshot(session, offset=offset)

    def _snapshot(
        self,
        session: _Session,
        error: str = "",
        *,
        offset: int = 0,
        stale: bool = False,
        canceled: bool = False,
    ) -> Dict[str, Any]:
        outbox = session.transport.outbox[offset:]
        messages = _messages(outbox)
        tools = _buttons(outbox)
        awaiting = bool(session.event is not None and broker.has_waiter(session.event.scene_key))
        done = session.task is None or session.task.done()
        effective_error = error or session.error
        state = build_state(
            session.transport.projection,
            operation=session.operation,
            turn=session.turn,
            awaiting=awaiting,
            done=done,
            error=effective_error,
            battle_view=session.transport.battle_view,
        )
        options = extract_options(session.transport.outbox, awaiting=awaiting)
        return {
            "ok": not effective_error,
            "error": effective_error,
            "operation": session.operation,
            "turn": session.turn,
            "offset": len(session.transport.outbox),
            "messages": messages,
            "buttons": tools,
            "options": options,
            "state": state,
            "battle": state.get("battle"),
            "legal_actions": list(ALLOWED_ACTIONS),
            "awaiting": awaiting,
            "done": done,
            "stale": stale,
            "canceled": canceled,
            "last_action": dict(session.last_action),
            "text": "\n".join(m.get("text", "") for m in messages if m.get("text")),
            "images": [
                seg["data"]
                for msg in messages
                for seg in msg.get("segments", [])
                if seg.get("type") == "image"
            ],
        }

    async def _cancel_locked(self, session: _Session) -> None:
        if session.task is not None and not session.task.done():
            session.task.cancel()
            try:
                await session.task
            except asyncio.CancelledError:
                pass
        if session.bot is not None:
            session.bot.release_interactions()

    async def cancel(self, session: _Session) -> None:
        async with session.lock:
            await self._cancel_locked(session)
            session.transport.battle_view = None
        session.error = "已取消当前连续交互。"

    def clear(self) -> None:
        """测试/停机用：清空所有网页会话。"""

        self._sessions.clear()


registry = WebSessionRegistry()

__all__ = ["WebSessionRegistry", "registry"]

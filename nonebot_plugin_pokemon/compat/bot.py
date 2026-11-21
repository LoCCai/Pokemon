"""gsuid_core ``Bot`` 的兼容实现。"""

from __future__ import annotations

import asyncio
from typing import Any, Iterable, List, Optional, Union

from .logger import logger
from .message_models import Button
from .models import Event
from ..platform.interaction import broker
from ..platform.message import OutMessage, Segment


def _normalize_buttons(option_list: Any) -> List[Button]:
    result: List[Button] = []

    def walk(item: Any) -> None:
        if item is None:
            return
        if isinstance(item, (list, tuple)):
            for sub in item:
                walk(sub)
            return
        if isinstance(item, Button):
            result.append(item)
            return
        text = str(item)
        result.append(Button(text=text, data=text, pressed_text=text, action=2))

    walk(option_list)
    return result


class Bot:
    """每个事件一个 Bot 实例，绑定当前会话的 transport。"""

    def __init__(self, ev: Event, transport: Any = None, default_timeout: Optional[float] = None):
        self.ev = ev
        self.transport = transport
        self.uid = ev.user_id or "0"
        self.bid = ev.bot_id or "0"
        self.bot_id = ev.bot_id
        self.bot_self_id = ev.bot_self_id
        if default_timeout is None:
            try:
                from ..config import plugin_config

                default_timeout = float(plugin_config.pokemon_interaction_timeout)
            except Exception:
                default_timeout = 60.0
        self.default_timeout = default_timeout
        self._multi_attached: Optional[str] = None

    # ---------------------------------------------------------------- 发送
    async def send(
        self,
        message: Any = None,
        at_sender: bool = False,
        extra_metadata: Any = None,
        wait_recall: bool = False,
    ) -> Any:
        if message is None:
            return None
        out = OutMessage.coerce(message)
        if self.transport is None:
            return None
        return await self.transport.send(out, at_sender=at_sender)

    async def send_option(
        self,
        reply: Any = None,
        option_list: Any = None,
        unsuported_platform: bool = False,
        sep: str = "\n",
        command_tips: str = "请输入以下命令之一:",
        command_start_text: str = "",
        at_sender: bool = False,
        **kwargs: Any,
    ) -> None:
        await self._send_with_options(reply, option_list, at_sender=at_sender)

    async def _send_with_options(
        self,
        reply: Any,
        option_list: Any,
        *,
        at_sender: bool = False,
        default_text: str = "",
    ) -> None:
        if reply is None:
            reply = default_text or None
        if reply is None and not option_list:
            return
        out = OutMessage.coerce(reply) if reply is not None else OutMessage()
        buttons = _normalize_buttons(option_list)
        if buttons:
            out.segments.append(Segment("buttons", buttons))
        if not out.segments:
            return
        if self.transport is None:
            return
        await self.transport.send(out, at_sender=at_sender)

    # ---------------------------------------------------------------- 等待
    async def _wait_event(self, key: str, queue: asyncio.Queue, timeout: float) -> Optional[Event]:
        try:
            return await asyncio.wait_for(queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.info(f"[pokemon] 会话 {key} 等待用户回复超时（{timeout:.0f}s）")
            return None

    async def receive_resp(
        self,
        reply: Any = None,
        option_list: Any = None,
        unsuported_platform: bool = False,
        is_mutiply: bool = False,
        is_recive: bool = True,
        timeout: float = 60,
        sep: str = "\n",
        command_tips: str = "请输入以下命令之一:",
        command_start_text: str = "",
        at_sender: bool = False,
        **kwargs: Any,
    ) -> Optional[Event]:
        if not is_recive:
            await self._send_with_options(
                reply,
                option_list,
                at_sender=at_sender,
                default_text=f"请在{timeout:.0f}秒内做出选择...",
            )
            return None

        key = self.ev.scene_key
        if self.default_timeout is not None:
            timeout = min(float(timeout), float(self.default_timeout))
        if is_mutiply:
            queue = broker.attach(key)
            self._multi_attached = key
        else:
            queue = broker.register(key)

        await self._send_with_options(
            reply,
            option_list,
            at_sender=at_sender,
            default_text=f"请在{timeout:.0f}秒内做出选择...",
        )
        try:
            result = await self._wait_event(key, queue, timeout)
        finally:
            if not is_mutiply:
                broker.unregister(key)
        return result

    async def receive_mutiply_resp(
        self,
        reply: Any = None,
        option_list: Any = None,
        unsuported_platform: bool = False,
        timeout: float = 60,
        sep: str = "\n",
        command_tips: str = "请输入以下命令之一:",
        command_start_text: str = "",
        **kwargs: Any,
    ) -> Optional[Event]:
        return await self.receive_resp(
            reply,
            option_list,
            unsuported_platform=unsuported_platform,
            is_mutiply=True,
            is_recive=True,
            timeout=timeout,
            sep=sep,
            command_tips=command_tips,
            command_start_text=command_start_text,
            **kwargs,
        )

    # ---------------------------------------------------------------- 收尾
    def release_interactions(self) -> None:
        if self._multi_attached:
            broker.detach(self._multi_attached)
            self._multi_attached = None


__all__ = ["Bot"]

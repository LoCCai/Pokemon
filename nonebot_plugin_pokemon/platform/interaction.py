"""交互会话路由。

战斗/小游戏会调用 ``bot.receive_resp`` / ``receive_mutiply_resp`` 等待下一条
用户消息。分发 Matcher 在收到消息时先查这里：如果该会话正在等待，就把事件
投递给等待者，而不是当成新命令执行。
"""

from __future__ import annotations

import asyncio
from typing import Dict, Optional, Set

from ..compat.models import Event


class InteractionBroker:
    def __init__(self) -> None:
        self._queues: Dict[str, asyncio.Queue] = {}
        self._persistent: Set[str] = set()

    def has_waiter(self, key: str) -> bool:
        return key in self._queues

    def feed(self, event: Event) -> bool:
        queue = self._queues.get(event.scene_key)
        if queue is None:
            return False
        # 交互回复直接把原文作为参数文本，游戏代码读取 resp.text
        event.text = event.raw_text
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            return False
        return True

    def register(self, key: str) -> asyncio.Queue:
        queue = self._queues.get(key)
        if queue is None:
            queue = asyncio.Queue(maxsize=32)
            self._queues[key] = queue
        return queue

    def unregister(self, key: str) -> None:
        if key in self._persistent:
            return
        self._queues.pop(key, None)

    def attach(self, key: str) -> asyncio.Queue:
        queue = self.register(key)
        self._persistent.add(key)
        return queue

    def detach(self, key: str) -> None:
        self._persistent.discard(key)
        self._queues.pop(key, None)

    def clear(self) -> None:
        self._queues.clear()
        self._persistent.clear()


broker = InteractionBroker()

__all__ = ["InteractionBroker", "broker"]

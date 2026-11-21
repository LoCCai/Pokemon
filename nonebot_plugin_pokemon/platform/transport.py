"""传输层：真实适配器发送 / 网页会话捕获。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from .message import OutMessage
from .sender import SendResult, send_message


class AdapterTransport:
    """把消息交给当前 NoneBot2 适配器发送。"""

    def __init__(self, bot: Any, event: Any, kind: str):
        self.bot = bot
        self.event = event
        self.kind = kind

    async def send(self, message: OutMessage, at_sender: bool = False) -> SendResult:
        return await send_message(self.bot, self.event, message, at_sender=at_sender, kind=self.kind)


@dataclass
class WebTransport:
    """网页会话：不出网，只记录出站消息。"""

    user_id: str = "web-guest"
    user_name: str = "网页玩家"
    is_admin: bool = False
    outbox: List[OutMessage] = field(default_factory=list)
    results: List[SendResult] = field(default_factory=list)
    kind: str = "web"

    async def send(self, message: OutMessage, at_sender: bool = False) -> SendResult:
        self.outbox.append(message)
        result = SendResult.from_message(message)
        self.results.append(result)
        return result


__all__ = ["AdapterTransport", "WebTransport"]

"""传输层：真实适配器发送 / 网页会话捕获。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

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

    user_id: str = ""
    user_name: str = ""
    is_admin: bool = False
    outbox: List[OutMessage] = field(default_factory=list)
    results: List[SendResult] = field(default_factory=list)
    kind: str = "web"
    battle_view: Optional[Dict[str, Any]] = None
    # Passive semantic projection of the real core output. Never mutates the
    # game, never recomputes formulas; see platform.projection.
    projection: Dict[str, Any] = field(default_factory=dict)

    def observe(self, message: OutMessage) -> None:
        try:
            from .projection import observe_message

            observe_message(self.projection, message)
        except Exception:
            # Projection is a best-effort read-only side channel; it must never
            # break the original gameplay send path.
            pass

    async def send(self, message: OutMessage, at_sender: bool = False) -> SendResult:
        self.observe(message)
        self.outbox.append(message)
        result = SendResult.from_message(message)
        self.results.append(result)
        return result


__all__ = ["AdapterTransport", "WebTransport"]

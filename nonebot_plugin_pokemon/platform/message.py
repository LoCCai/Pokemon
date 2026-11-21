"""统一的出站消息模型。"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Any, Iterable, List, Optional, Union

from PIL import Image

from ..compat.message_models import Button
from ..compat.segment import ImagePayload, Message, image_bytes


@dataclass
class Segment:
    type: str
    data: Any = None

    def to_dict(self) -> dict:
        if self.type == "image" and isinstance(self.data, (bytes, bytearray)):
            return {
                "type": "image",
                "mime": getattr(self.data, "mime", "image/jpeg"),
                "base64": base64.b64encode(bytes(self.data)).decode(),
            }
        if self.type == "buttons":
            return {"type": "buttons", "data": [b.to_dict() for b in self.data]}
        return {"type": self.type, "data": self.data}


@dataclass
class OutMessage:
    segments: List[Segment] = field(default_factory=list)

    # ---------------------------------------------------------------- 构造
    @classmethod
    def coerce(cls, message: Any) -> "OutMessage":
        out = cls()
        out.extend(message)
        return out

    def extend(self, message: Any) -> None:
        if message is None:
            return
        if isinstance(message, OutMessage):
            self.segments.extend(message.segments)
        elif isinstance(message, str):
            if message.startswith("base64://"):
                self.segments.append(Segment("image", image_bytes(message)))
            else:
                self.segments.append(Segment("text", message))
        elif isinstance(message, ImagePayload):
            self.segments.append(Segment("image", message))
        elif isinstance(message, (bytes, bytearray, memoryview)):
            self.segments.append(Segment("image", image_bytes(bytes(message))))
        elif isinstance(message, Image.Image):
            self.segments.append(Segment("image", image_bytes(message)))
        elif isinstance(message, Message):
            self._from_compat(message)
        elif isinstance(message, (list, tuple)):
            for item in message:
                self.extend(item)
        else:
            self.segments.append(Segment("text", str(message)))

    def _from_compat(self, message: Message) -> None:
        if message.type == "text":
            self.segments.append(Segment("text", str(message.data)))
        elif message.type == "image":
            data = message.data
            if isinstance(data, str) and data.startswith(("http://", "https://")):
                self.segments.append(Segment("image", data))
            elif isinstance(data, str) and data.startswith("base64://"):
                self.segments.append(Segment("image", image_bytes(data)))
            else:
                self.segments.append(Segment("image", image_bytes(data)))
        elif message.type == "at":
            self.segments.append(Segment("at", str(message.data)))
        elif message.type == "buttons":
            self.segments.append(Segment("buttons", list(message.data or [])))
        elif message.type == "node":
            for item in message.data or []:
                self._from_compat(item)
        elif message.type == "file":
            # (name, content) 或 content
            self.segments.append(Segment("file", message.data))
        elif message.type == "record":
            self.segments.append(Segment("record", message.data))
        elif message.type == "video":
            self.segments.append(Segment("video", message.data))
        else:
            self.segments.append(Segment(message.type, message.data))

    # ---------------------------------------------------------------- 查询
    @property
    def plain_text(self) -> str:
        return "".join(str(s.data) for s in self.segments if s.type == "text")

    @property
    def images(self) -> List[Any]:
        return [s.data for s in self.segments if s.type == "image"]

    @property
    def buttons(self) -> List[Button]:
        result: List[Button] = []
        for seg in self.segments:
            if seg.type == "buttons":
                result.extend(seg.data)
        return result

    @property
    def has_content(self) -> bool:
        return bool(self.segments)

    def with_buttons(self, buttons: Optional[Iterable[Button]]) -> "OutMessage":
        if buttons:
            self.segments.append(Segment("buttons", list(buttons)))
        return self

    def text_and_button_hint(self, sep: str = "\n", title: str = "请输入以下命令之一:") -> str:
        """给不支持按钮的平台生成纯文本选项提示。"""

        lines: List[str] = []
        for button in self.buttons:
            data = button.data or button.text
            if data and data not in lines:
                lines.append(data)
        if not lines:
            return ""
        return f"\n{title}\n" + sep.join(lines)


__all__ = ["OutMessage", "Segment"]

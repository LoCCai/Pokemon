"""消息段兼容层。

游戏代码只直接构造 ``MessageSegment.text`` / ``MessageSegment.image``。
本模块返回轻量的 :class:`Message`，由平台层转换成各协议自己的消息段。
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable, List, Union

from PIL import Image


@dataclass
class Message:
    type: str
    data: Any = None


class ImagePayload(bytes):
    """带 MIME 信息的图片字节，平台层据此选择 JPEG/PNG。"""

    mime: str = "image/jpeg"

    def __new__(cls, data: bytes, mime: str = "image/jpeg"):
        obj = super().__new__(cls, data)
        obj.mime = mime
        return obj


def image_bytes(img: Union[str, Path, bytes, Image.Image]) -> ImagePayload:
    """把多种图片来源规范化为 JPEG 字节。"""

    if isinstance(img, Image.Image):
        buffer = BytesIO()
        if getattr(img, "format", None) == "GIF":
            img.save(buffer, format="GIF")
            return ImagePayload(buffer.getvalue(), "image/gif")
        img.convert("RGB").save(buffer, format="JPEG", quality=92)
        return ImagePayload(buffer.getvalue(), "image/jpeg")
    if isinstance(img, (bytes, bytearray, memoryview)):
        data = bytes(img)
        mime = "image/jpeg"
        if data.startswith(b"\x89PNG"):
            mime = "image/png"
        elif data.startswith(b"GIF"):
            mime = "image/gif"
        return ImagePayload(data, mime)
    if isinstance(img, Path):
        return image_bytes(img.read_bytes())
    text = str(img)
    if text.startswith("base64://"):
        data = base64.b64decode(text[9:])
        return image_bytes(data)
    if text.startswith("data:image/"):
        header, _, payload = text.partition(",")
        mime = header[5:].split(";")[0] or "image/png"
        return ImagePayload(base64.b64decode(payload), mime)
    with open(text, "rb") as fp:
        return image_bytes(fp.read())


class MessageSegment:
    @staticmethod
    def text(content: str) -> Message:
        return Message("text", str(content))

    @staticmethod
    def image(img: Union[str, Path, bytes, Image.Image]) -> Message:
        if isinstance(img, str) and img.startswith(("http://", "https://")):
            return Message("image", img)
        if isinstance(img, str) and img.startswith("base64://"):
            return Message("image", img)
        return Message("image", image_bytes(img))

    @staticmethod
    def at(user: Union[str, int]) -> Message:
        return Message("at", str(user))

    @staticmethod
    def buttons(buttons: Any) -> Message:
        return Message("buttons", buttons)

    @staticmethod
    def node(content_list: Iterable[Union[Message, str, bytes]]) -> Message:
        items: List[Message] = []
        for item in content_list:
            if isinstance(item, Message):
                items.append(item)
            elif isinstance(item, (bytes, bytearray, memoryview)):
                items.append(MessageSegment.image(bytes(item)))
            else:
                text = str(item)
                if text.startswith(("base64://", "http://", "https://", "file://")):
                    items.append(Message("image", text))
                else:
                    items.append(MessageSegment.text(text))
        return Message("node", items)

    @staticmethod
    def record(content: Any) -> Message:
        return Message("record", content)

    @staticmethod
    def file(content: Any, file_name: str) -> Message:
        return Message("file", (file_name, content))

    @staticmethod
    def video(content: Any) -> Message:
        return Message("video", content)


__all__ = ["ImagePayload", "Message", "MessageSegment", "image_bytes"]

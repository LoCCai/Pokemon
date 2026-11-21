"""图片转换兼容层（对应 gsuid_core.utils.image.convert.convert_img）。"""

from __future__ import annotations

from pathlib import Path
from typing import Union

from PIL import Image

from .media import open_image
from .segment import ImagePayload, image_bytes


async def convert_img(
    img: Union[Image.Image, str, Path, bytes],
    is_base64: bool = False,
) -> Union[ImagePayload, str]:
    """把 PIL 图片 / 路径 / 字节转换为可发送的图片负载。

    素材缺失时使用占位图，保证指令不因单张图标缺失而失败。
    ``is_base64=True`` 时返回 ``base64://`` 字符串。
    """

    if isinstance(img, Image.Image):
        payload = image_bytes(img)
    elif isinstance(img, (bytes, bytearray, memoryview)):
        payload = image_bytes(bytes(img))
    else:
        payload = image_bytes(open_image(img))
    if is_base64:
        import base64

        return "base64://" + base64.b64encode(payload).decode()
    return payload


__all__ = ["convert_img"]

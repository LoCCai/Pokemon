"""安全图片打开：素材缺失时返回占位图，并在后台补下载。"""

from __future__ import annotations

from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Any, Tuple, Union

from PIL import Image, ImageDraw

from ..resources.downloader import enqueue_missing


@lru_cache(maxsize=32)
def placeholder(size: Tuple[int, int] = (300, 300)) -> Image.Image:
    width, height = size
    image = Image.new("RGBA", (width, height), (32, 36, 48, 255))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (4, 4, width - 4, height - 4),
        radius=max(8, min(width, height) // 12),
        outline=(120, 170, 255, 255),
        width=max(2, min(width, height) // 60),
        fill=(44, 50, 66, 255),
    )
    draw.text(
        (width / 2, height / 2),
        "?",
        fill=(190, 210, 255, 255),
        anchor="mm",
        font_size=max(14, min(width, height) // 3),
    )
    return image


def open_image(
    source: Union[str, Path, bytes, Any],
    size: Tuple[int, int] = (300, 300),
    *,
    missing: bool = True,
) -> Image.Image:
    """打开图片；失败时返回占位图。

    ``source`` 可以是路径、``BytesIO``、bytes。路径不存在时会尝试排队补下载。
    """

    try:
        if isinstance(source, Image.Image):
            return source.copy()
        if isinstance(source, (bytes, bytearray, memoryview)):
            return Image.open(BytesIO(bytes(source)))
        if hasattr(source, "read"):
            return Image.open(source)
        path = Path(source)
        if path.exists() and path.stat().st_size > 0:
            return Image.open(path)
        if missing:
            enqueue_missing(path)
    except Exception:
        pass
    return placeholder(size).copy()


__all__ = ["open_image", "placeholder"]

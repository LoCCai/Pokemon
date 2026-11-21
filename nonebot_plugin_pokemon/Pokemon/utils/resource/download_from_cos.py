"""兼容旧入口：把素材下载委托给 NoneBot2 分支的下载器。"""

from __future__ import annotations

from ....resources.downloader import download_all
from .RESOURCE_PATH import CHAR_ICON_PATH, CHAR_ICON_S_PATH


async def check_use() -> str:
    return await download_all()


__all__ = ["check_use", "CHAR_ICON_PATH", "CHAR_ICON_S_PATH"]
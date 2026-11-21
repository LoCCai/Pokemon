"""日志兼容层。"""

from __future__ import annotations

import logging

try:  # NoneBot 已初始化时优先使用其 loguru logger
    from nonebot.log import logger as logger
except Exception:  # pragma: no cover - 纯离线测试
    logger = logging.getLogger("nonebot_plugin_pokemon")  # type: ignore[assignment]

__all__ = ["logger"]

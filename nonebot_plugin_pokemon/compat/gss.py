"""主动推送 Bot 注册表（兼容 gsuid_core.gss）。

上游用 ``gss.active_bot[bot_id].target_send(...)`` 给群推送大量出现信息。
平台层在收到消息时把当前 Bot 注册进来；推送时会自动选择已注册的可用 Bot。
"""

from __future__ import annotations

from typing import Any, Dict


class _GSS:
    active_bot: Dict[str, Any] = {}


gss = _GSS()

__all__ = ["gss"]

"""gsuid_core ``Event`` 的兼容实现。

只保留 Pokemon 插件实际使用的字段，并在平台层把 OneBot v11 / v12 / QQ 官方
机器人与网页会话统一映射到这个对象。字段名称与 gsuid_core 保持一致，方便
上游游戏代码几乎零修改地运行。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Event:
    # 机器人 / 会话标识
    bot_id: str = "Bot"
    bot_self_id: str = ""
    msg_id: str = ""
    user_type: str = "group"  # group / direct / channel / sub_channel / web
    group_id: Optional[str] = None
    user_id: str = ""
    sender: Dict[str, Any] = field(default_factory=dict)
    user_pm: int = 6

    # 文本与触发信息
    raw_text: str = ""
    command: str = ""
    text: str = ""
    at: Optional[str] = None
    at_list: List[Any] = field(default_factory=list)
    is_tome: bool = False
    at_bot: bool = False
    regex_group: tuple = ()
    regex_dict: Dict[str, str] = field(default_factory=dict)

    # 平台原始对象
    raw_event: Any = None
    platform: str = ""
    transport: Any = None
    session_id: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def scene_key(self) -> str:
        """交互等待使用的会话键（必须区分用户，避免同群其他人误触发战斗）。"""

        target = self.group_id if self.user_type not in {"direct", "private"} else "-"
        return f"{self.platform}:{self.bot_self_id}:{self.user_type}:{target}:{self.user_id}"

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __hash__(self) -> int:
        return hash((self.platform, self.bot_self_id, self.user_type, self.group_id, self.user_id))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Event):
            return NotImplemented
        return (
            self.platform,
            self.bot_self_id,
            self.user_type,
            self.group_id,
            self.user_id,
        ) == (
            other.platform,
            other.bot_self_id,
            other.user_type,
            other.group_id,
            other.user_id,
        )


__all__ = ["Event"]

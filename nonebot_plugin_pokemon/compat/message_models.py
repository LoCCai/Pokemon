"""gsuid_core ``Button`` 的兼容实现（字段顺序与上游 msgspec Struct 一致）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Optional, Union


@dataclass
class Button:
    text: str
    data: str
    pressed_text: Optional[str] = None
    style: Literal[0, 1] = 1
    action: Literal[-1, 0, 1, 2] = -1
    permisson: Literal[0, 1, 2, 3] = 2
    specify_role_ids: List[str] = field(default_factory=list)
    specify_user_ids: List[str] = field(default_factory=list)
    unsupport_tips: str = "您的客户端暂不支持该功能, 请升级后适配..."
    prefix: str = ""
    _edited: bool = False

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "data": self.data,
            "pressed_text": self.pressed_text,
            "style": self.style,
            "action": self.action,
            "permisson": self.permisson,
        }


ButtonType = Union[List[str], List[Button], List[List[str]], List[List[Button]]]
ButtonList = Union[List[Button], List[List[Button]]]

__all__ = ["Button", "ButtonType", "ButtonList"]

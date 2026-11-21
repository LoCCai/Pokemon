"""gsuid_core ``SV`` 的兼容实现。

上游 Pokemon 插件用 ``SV.on_fullmatch / on_command / on_prefix`` 注册了约 100 个
指令。这里把注册信息收进一个进程内注册表，由 NoneBot2 的统一分发 Matcher
按 (priority, 触发类型, 命令长度) 选出唯一命中的处理器。

匹配语义尽量贴近 gsuid_core：
* ``on_fullmatch``：忽略首尾空白后完全相等；
* ``on_command``：以命令词开头，余下部分作为参数（命令词与参数之间可有空格）；
* ``on_prefix``：以命令词开头且必须有后续内容；
* 中文/英文交界处允许省略空格，例如 ``精灵图鉴皮卡丘``。
"""

from __future__ import annotations

import inspect
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Literal, Optional

GAP = " \t\u3000\u00a0"

_TYPE_RANK: dict[str, int] = {
    "fullmatch": 0,
    "command": 1,
    "prefix": 2,
    "suffix": 2,
    "regex": 3,
    "keyword": 4,
    "message": 9,
}


def _is_cjk(ch: str) -> bool:
    code = ord(ch)
    return 0x3400 <= code <= 0x4DBF or 0x4E00 <= code <= 0x9FFF


def _boundary(left: str, right: str) -> bool:
    return (_is_cjk(left) and right.isascii() and right.isalnum()) or (
        left.isascii() and left.isalnum() and _is_cjk(right)
    )


def consume_keyword(text: str, keyword: str) -> Optional[int]:
    """返回 keyword 在 text 开头消耗的字符数；不匹配返回 None。"""

    i = 0
    j = 0
    while j < len(keyword):
        if i >= len(text):
            return None
        key_ch = keyword[j]
        text_ch = text[i]
        if key_ch in GAP:
            if text_ch not in GAP:
                return None
            while j < len(keyword) and keyword[j] in GAP:
                j += 1
            while i < len(text) and text[i] in GAP:
                i += 1
            continue
        if text_ch in GAP:
            if j > 0 and _boundary(keyword[j - 1], key_ch):
                while i < len(text) and text[i] in GAP:
                    i += 1
                continue
            return None
        if text_ch != key_ch:
            return None
        i += 1
        j += 1
    return i


@dataclass
class Trigger:
    type: str
    keyword: str
    func: Callable
    sv: "SV"
    block: bool = False
    to_me: bool = False
    order: int = 0

    def matches(self, text: str) -> Optional[str]:
        """命中时返回参数文本，未命中返回 None。"""

        text = text.strip(GAP)
        keyword = self.keyword
        if self.type == "fullmatch":
            if text == keyword:
                return ""
            return None
        if self.type == "command":
            end = consume_keyword(text, keyword)
            if end is None:
                return None
            return text[end:].lstrip(GAP)
        if self.type == "prefix":
            end = consume_keyword(text, keyword)
            if end is None or end >= len(text):
                return None
            return text[end:].lstrip(GAP)
        if self.type == "suffix":
            if text.endswith(keyword) and text != keyword:
                return text[: -len(keyword)].rstrip(GAP)
            return None
        if self.type == "keyword":
            return "" if keyword in text else None
        if self.type == "regex":
            match = re.search(keyword, text)
            if not match:
                return None
            self._last_match = match  # type: ignore[attr-defined]
            return text
        if self.type == "message":
            return text
        return None

    @property
    def specificity(self) -> tuple:
        return (
            self.sv.priority,
            _TYPE_RANK.get(self.type, 9),
            -len(self.keyword),
            self.order,
        )


class SV:
    """同名 SV 共享实例与触发器，和 gsuid_core 的行为一致。"""

    _registry: dict[str, "SV"] = {}
    _order: int = 0

    def __new__(cls, name: str = "", *args: Any, **kwargs: Any) -> "SV":
        if not name:
            raise ValueError("SV.name is required")
        if name in cls._registry:
            return cls._registry[name]
        obj = super().__new__(cls)
        cls._registry[name] = obj
        return obj

    def __init__(
        self,
        name: str = "",
        pm: int = 6,
        priority: int = 5,
        enabled: bool = True,
        area: str = "ALL",
        black_list: Optional[list] = None,
        white_list: Optional[list] = None,
        **_: Any,
    ) -> None:
        if getattr(self, "_initialized", False):
            return
        self.name = name
        self.pm = pm
        self.priority = priority
        self.enabled = enabled
        self.area = area
        self.black_list = list(black_list or [])
        self.white_list = list(white_list or [])
        self.triggers: list[Trigger] = []
        self._initialized = True

    # ------------------------------------------------------------ 注册
    def _on(self, kind: str, keyword: Any, **options: Any) -> Callable:
        if isinstance(keyword, str):
            keywords = (keyword,)
        else:
            keywords = tuple(keyword)

        def decorator(func: Callable) -> Callable:
            for word in keywords:
                if not word:
                    continue
                duplicate = any(
                    t.type == kind and t.keyword == word and t.func is func
                    for t in self.triggers
                )
                if duplicate:
                    continue
                SV._order += 1
                self.triggers.append(
                    Trigger(
                        type=kind,
                        keyword=word,
                        func=func,
                        sv=self,
                        block=bool(options.get("block", False)),
                        to_me=bool(options.get("to_me", False)),
                        order=SV._order,
                    )
                )
            return func

        return decorator

    def on_fullmatch(self, keyword: Any, **options: Any) -> Callable:
        return self._on("fullmatch", keyword, **options)

    def on_command(self, keyword: Any, **options: Any) -> Callable:
        return self._on("command", keyword, **options)

    def on_prefix(self, keyword: Any, **options: Any) -> Callable:
        return self._on("prefix", keyword, **options)

    def on_suffix(self, keyword: Any, **options: Any) -> Callable:
        return self._on("suffix", keyword, **options)

    def on_keyword(self, keyword: Any, **options: Any) -> Callable:
        return self._on("keyword", keyword, **options)

    def on_regex(self, keyword: Any, **options: Any) -> Callable:
        return self._on("regex", keyword, **options)

    def on_message(self, unique_id: Any = None, **options: Any) -> Callable:
        return self._on("message", str(unique_id or "message"), **options)

    # ------------------------------------------------------------ 分发
    @classmethod
    def all_triggers(cls) -> list[Trigger]:
        result: list[Trigger] = []
        for sv in cls._registry.values():
            if sv.enabled:
                result.extend(sv.triggers)
        result.sort(key=lambda t: t.specificity)
        return result

    @classmethod
    def find(cls, text: str) -> Optional[tuple[Trigger, str]]:
        """返回最优命中的触发器与参数；没有命中返回 None。"""

        for trigger in cls.all_triggers():
            arg = trigger.matches(text)
            if arg is not None:
                return trigger, arg
        return None

    @classmethod
    def reset(cls) -> None:
        cls._registry.clear()
        cls._order = 0


def list_commands() -> list[dict[str, Any]]:
    """导出注册表，供菜单、LLM 与测试使用。"""

    result: list[dict[str, Any]] = []
    for trigger in SV.all_triggers():
        interactive = False
        try:
            source = inspect.getsource(trigger.func)
            interactive = "receive_resp" in source or "receive_mutiply_resp" in source
        except Exception:
            pass
        result.append(
            {
                "type": trigger.type,
                "keyword": trigger.keyword,
                "sv": trigger.sv.name,
                "pm": trigger.sv.pm,
                "priority": trigger.sv.priority,
                "handler": f"{trigger.func.__module__}.{trigger.func.__name__}",
                "interactive": interactive,
            }
        )
    return result


__all__ = ["SV", "Trigger", "consume_keyword", "list_commands"]

"""可信身份与权限归一化。

所有入口（聊天事件、宿主 QWeb 账号、MoEllmChats 工具上下文）都必须经过这里，
避免把客户端可声明的 ``is_admin`` / ``group_id`` 直接升级成权限。

约定：

* QWeb 宿主账号的 QQ 只读取 ``account.qq``；
* 管理员角色只读取 ``account.role``（或聊天平台的 ``sender.role``）；
* ``is_admin`` 永远由角色推导，不从请求体、查询参数、请求头或工具参数读取。
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

# 宿主与聊天平台常见的管理员角色写法；大小写不敏感。
ADMIN_ROLES = frozenset(
    {
        "admin",
        "administrator",
        "owner",
        "superadmin",
        "super_admin",
        "superuser",
        "super_user",
        "root",
    }
)

_MEMBER_ROLE = "member"


def text_of(value: Any) -> str:
    """把任意值安全转成去空白字符串。"""

    if value is None:
        return ""
    return str(value).strip()


def normalized_role(value: Any, *, default: str = _MEMBER_ROLE) -> str:
    """归一化角色名；空值退回 ``default``。"""

    role = text_of(value).lower()
    return role or default


def is_admin_role(value: Any) -> bool:
    """角色是否具备网页管理权限。"""

    return normalized_role(value, default="") in ADMIN_ROLES


def role_of(account: Any) -> str:
    """从宿主账号或聊天发送者中读取角色（只读 ``role`` 字段）。"""

    if account is None:
        return ""
    if isinstance(account, Mapping):
        return text_of(account.get("role"))
    return text_of(getattr(account, "role", None))


def qq_of(account: Any) -> str:
    """从宿主账号读取 QQ。

    真实宿主使用 ``src.qi_web.dependencies`` 的账号对象，其 QQ 字段固定为
    ``account.qq``。这里不读取 ``user_id`` / ``id`` / 请求头，避免客户端用
    其他字段冒充。
    """

    if account is None:
        return ""
    if isinstance(account, Mapping):
        return text_of(account.get("qq"))
    return text_of(getattr(account, "qq", None))


def name_of(account: Any) -> str:
    """读取宿主账号的展示名；没有则返回空字符串，由调用方决定回退。"""

    if account is None:
        return ""
    if isinstance(account, Mapping):
        for key in ("nickname", "username", "name", "display_name"):
            value = text_of(account.get(key))
            if value:
                return value
        return ""
    for attr in ("nickname", "username", "name", "display_name"):
        value = text_of(getattr(account, attr, None))
        if value:
            return value
    return ""


def event_role(event: Any) -> str:
    """从兼容事件读取发送者角色。"""

    sender = getattr(event, "sender", None) or {}
    if isinstance(sender, Mapping):
        return normalized_role(sender.get("role"))
    return normalized_role(getattr(sender, "role", None))


def event_is_admin(event: Any) -> bool:
    """网页事件只按角色判定管理员，不读取 NoneBot SUPERUSERS。"""

    return is_admin_role(event_role(event))


def effective_role(role: Any = None, *, is_admin: Optional[bool] = None) -> str:
    """内部调用兼容：显式角色优先，否则才使用可信调用方传入的旧 ``is_admin``。

    该函数只在插件内部（聊天事件、宿主桥接）使用；HTTP 请求与工具参数绝不会
    把 ``is_admin`` 传到这里。
    """

    normalized = normalized_role(role, default="")
    if normalized:
        return normalized
    return "admin" if is_admin else _MEMBER_ROLE


__all__ = [
    "ADMIN_ROLES",
    "effective_role",
    "event_is_admin",
    "event_role",
    "is_admin_role",
    "name_of",
    "normalized_role",
    "qq_of",
    "role_of",
    "text_of",
]
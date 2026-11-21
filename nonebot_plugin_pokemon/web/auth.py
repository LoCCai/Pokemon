"""QWeb 宿主认证适配。

七七分支只接受真实宿主 ``src.qi_web.dependencies`` 提供的 FastAPI 依赖：

* ``require_membership``：要求登录成员，返回 ``account``；
* ``admin_account``：要求管理员，返回 ``account``；
* ``csrf_protected``：校验 ``X-CSRF-Token``（宿主自己决定 token 来源）。

插件不会读取 ``X-QWeb-User-Id``、``X-QWeb-Is-Admin``、查询参数或 Cookie 来
声明身份；QQ 只来自 ``account.qq``，管理员只来自 ``account.role``。

没有安装宿主时，默认不挂载网页；离线测试可以通过 :class:`AuthDependencies`
显式注入假依赖。未注入依赖却直接访问路由会得到 503，而不会以游客/假身份放行。
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any, Callable, Optional

from fastapi import Depends, HTTPException, Request

from ..compat.logger import logger
from ..identity import is_admin_role, name_of, normalized_role, qq_of, role_of

HOST_MODULE = "src.qi_web.dependencies"


@dataclass(frozen=True)
class WebAccount:
    """从宿主账号对象提取出的最小可信身份。"""

    qq: str
    role: str = "member"
    user_name: str = ""
    raw: Any = None

    @property
    def is_admin(self) -> bool:
        return is_admin_role(self.role)

    def to_context(self, *, platform: str = "qweb") -> Any:
        from ..llm.tools import ToolContextData

        return ToolContextData(
            user_id=self.qq,
            group_id=None,
            user_name=self.user_name or self.qq,
            is_admin=self.is_admin,
            platform=platform,
            role=self.role,
        )

    @classmethod
    def from_host(cls, account: Any) -> "WebAccount":
        """严格从 ``account.qq`` / ``account.role`` 构建身份。"""

        if isinstance(account, cls):
            return account
        qq = qq_of(account)
        if not qq:
            raise HTTPException(status_code=401, detail="宿主未提供成员 QQ")
        role = normalized_role(role_of(account))
        user_name = name_of(account) or qq
        return cls(qq=qq, role=role, user_name=user_name, raw=account)


@dataclass(frozen=True)
class AuthDependencies:
    """宿主注入的三个 FastAPI 依赖。"""

    require_membership: Callable[..., Any]
    admin_account: Callable[..., Any]
    csrf_protected: Callable[..., Any]

    @classmethod
    def from_module(cls, module: Any) -> Optional["AuthDependencies"]:
        try:
            membership = getattr(module, "require_membership")
            admin = getattr(module, "admin_account")
            csrf = getattr(module, "csrf_protected")
        except AttributeError:
            return None
        if not all(callable(item) for item in (membership, admin, csrf)):
            return None
        return cls(require_membership=membership, admin_account=admin, csrf_protected=csrf)


def load_host_auth(module_name: str = HOST_MODULE) -> Optional[AuthDependencies]:
    """尝试导入真实宿主依赖；不可用时返回 ``None``。"""

    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        logger.debug(f"[pokemon] 未接入 QWeb 宿主 {module_name}: {exc}")
        return None
    auth = AuthDependencies.from_module(module)
    if auth is None:
        logger.warning(f"[pokemon] {module_name} 缺少 require_membership/admin_account/csrf_protected")
    return auth


async def _unavailable() -> None:
    raise HTTPException(status_code=503, detail="QWeb 宿主认证未接入，网页玩法已关闭")


def unavailable_auth() -> AuthDependencies:
    """占位依赖：任何请求都被拒绝，绝不回退到游客/假身份。"""

    return AuthDependencies(
        require_membership=_unavailable,
        admin_account=_unavailable,
        csrf_protected=_unavailable,
    )


def member_account_dependency(auth: AuthDependencies) -> Callable[..., Any]:
    """构造返回 :class:`WebAccount` 的 FastAPI 成员依赖。"""

    async def member_account(
        request: Request,
        account: Any = Depends(auth.require_membership),
    ) -> WebAccount:
        if account is None:
            # 某些宿主只做校验，把账号放在 request.state.account。
            account = getattr(request.state, "account", None)
        if account is None:
            raise HTTPException(status_code=401, detail="未登录")
        return WebAccount.from_host(account)

    member_account.__name__ = "pokemon_qweb_member_account"
    return member_account


def admin_account_dependency(auth: AuthDependencies) -> Callable[..., Any]:
    """构造返回管理员 :class:`WebAccount` 的 FastAPI 依赖。"""

    async def admin_account(
        request: Request,
        account: Any = Depends(auth.admin_account),
    ) -> WebAccount:
        if account is None:
            account = getattr(request.state, "account", None)
        if account is None:
            raise HTTPException(status_code=403, detail="需要管理员身份")
        resolved = WebAccount.from_host(account)
        if not resolved.is_admin:
            raise HTTPException(status_code=403, detail="需要管理员身份")
        return resolved

    admin_account.__name__ = "pokemon_qweb_admin_account"
    return admin_account


__all__ = [
    "AuthDependencies",
    "HOST_MODULE",
    "WebAccount",
    "admin_account_dependency",
    "load_host_auth",
    "member_account_dependency",
    "unavailable_auth",
]
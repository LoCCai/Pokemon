"""离线测试用的 QWeb 宿主依赖桩。

它不是插件的一部分，也不进入生产导入路径；测试通过 sys.modules 把它装成
``src.qi_web.dependencies``，验证插件确实调用宿主依赖，而不是自己读请求头。
"""

from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

from fastapi import Depends, Header, HTTPException, Request

CSRF_TOKEN = "test-csrf-token"
ACCOUNT_HEADER = "X-Test-Account"


async def require_membership(request: Request) -> SimpleNamespace:
    raw = request.headers.get(ACCOUNT_HEADER, "")
    role, sep, qq = raw.partition(":")
    if not sep or not qq:
        raise HTTPException(status_code=401, detail="测试宿主：缺少成员凭证")
    return SimpleNamespace(qq=qq, role=role or "member", nickname=f"Tester-{qq}")


async def admin_account(account: SimpleNamespace = Depends(require_membership)) -> SimpleNamespace:
    # 宿主自己的角色判定；不依赖插件实现，避免测试桩反向影响被测代码。
    role = str(getattr(account, "role", "") or "").lower()
    if role not in {"admin", "administrator", "owner", "superadmin", "super_admin", "root"}:
        raise HTTPException(status_code=403, detail="测试宿主：需要管理员")
    return account


async def csrf_protected(x_csrf_token: str = Header(default="", alias="X-CSRF-Token")) -> None:
    if x_csrf_token != CSRF_TOKEN:
        raise HTTPException(status_code=403, detail="测试宿主：CSRF 校验失败")


def install() -> ModuleType:
    """把假宿主依赖放进 sys.modules，供插件导入。"""

    src = ModuleType("src")
    src.__path__ = []  # type: ignore[attr-defined]
    qi_web = ModuleType("src.qi_web")
    qi_web.__path__ = []  # type: ignore[attr-defined]
    deps = ModuleType("src.qi_web.dependencies")
    deps.require_membership = require_membership
    deps.admin_account = admin_account
    deps.csrf_protected = csrf_protected
    qi_web.dependencies = deps
    src.qi_web = qi_web
    sys.modules["src"] = src
    sys.modules["src.qi_web"] = qi_web
    sys.modules["src.qi_web.dependencies"] = deps
    return deps


__all__ = ["ACCOUNT_HEADER", "CSRF_TOKEN", "admin_account", "csrf_protected", "install", "require_membership"]
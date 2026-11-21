"""QWeb 宿主适配帮助函数。

真实宿主是 ``src.qi_web.dependencies``，它提供三个 FastAPI 依赖：

* ``require_membership``：成员校验，返回带 ``qq`` / ``role`` 的账号；
* ``admin_account``：管理员校验，返回管理员账号；
* ``csrf_protected``：校验 ``X-CSRF-Token``。

插件只从 ``account.qq`` 取 QQ、从 ``account.role`` 取管理员角色。宿主的反向
代理/中间件不需要再注入 ``X-QWeb-User-Id`` 之类的身份头。没有宿主依赖时网页
默认不挂载；测试可以显式注入 :class:`nonebot_plugin_pokemon.web.auth.AuthDependencies`。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..menu import PLUGIN_ID, VERSION
from ..menu.catalog import build_entries
from .auth import AuthDependencies, load_host_auth
from .auth import HOST_MODULE  # re-export for integration docs/tests


def feature_catalog(*, include_hidden: bool = False) -> Dict[str, Any]:
    features: List[Dict[str, Any]] = []
    for entry in build_entries():
        if entry["pmn_hidden"] and not include_hidden:
            continue
        features.append(
            {
                "id": entry["id"],
                "name": entry["func"],
                "summary": entry["brief_des"],
                "category": entry["category"],
                "triggers": entry["triggers"],
                "llm_intents": entry["llm_intents"],
                "hidden": entry["pmn_hidden"],
                "permission": entry["permission"],
                "invocable": True,
                "details": entry["detail_des"],
            }
        )
    return {
        "plugin_id": PLUGIN_ID,
        "name": "宝可梦",
        "version": VERSION,
        "features": features,
    }


def mount(
    app: Any,
    prefix: str = "/qweb/pokemon",
    auth: Optional[AuthDependencies] = None,
) -> None:
    """把宝可梦 API 挂到宿主 FastAPI 应用。

    必须提供真实宿主依赖，或显式传入测试用 ``auth``；否则直接报错，避免出现
    “看起来挂载成功、实际没有认证”的空壳入口。
    """

    from .app import create_router

    auth = auth or load_host_auth()
    if auth is None:
        raise RuntimeError(
            f"QWeb 宿主认证未接入：无法导入 {HOST_MODULE}，"
            "拒绝在没有 require_membership/admin_account/csrf_protected 的情况下挂载"
        )
    app.include_router(create_router(auth), prefix=prefix.rstrip("/"), tags=["pokemon"])


__all__ = ["HOST_MODULE", "feature_catalog", "mount"]
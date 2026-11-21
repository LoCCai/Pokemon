"""QWeb 宿主适配帮助函数。

QWeb 宿主可以：

1. 直接把 :data:`nonebot_plugin_pokemon.web.app.router` 挂到自己的 FastAPI 应用；
2. 或使用插件默认挂载的 ``/qweb/pokemon`` 与 ``/qweb/admin/pokemon``；
3. 从 :func:`feature_catalog` 生成 QWeb Feature Catalog 条目；
4. 在反向代理层注入身份头（见 README「QWeb 接入约定」）。
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..menu import PLUGIN_ID, VERSION
from ..menu.catalog import build_entries


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


def mount(app: Any, prefix: str = "/qweb/pokemon") -> None:
    """把宝可梦 API 挂到宿主 FastAPI 应用。"""

    from .app import router

    app.include_router(router, prefix=prefix.rstrip("/"), tags=["pokemon"])


__all__ = ["feature_catalog", "mount"]

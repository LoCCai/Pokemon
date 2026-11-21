"""数据目录解析。

优先级：
1. ``POKEMON_DATA_DIR``（配置项 ``pokemon_data_dir``）；
2. ``nonebot-plugin-localstore`` 提供的插件数据目录；
3. 运行目录下的 ``data/pokemon``。

所有路径函数都延迟解析，避免在插件元数据导入阶段触发 NoneBot 初始化。
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
STATIC_DIR = PACKAGE_DIR / "web" / "static"


@lru_cache(maxsize=1)
def data_root() -> Path:
    """返回插件数据根目录（不存在时创建）。"""

    configured = os.getenv("POKEMON_DATA_DIR", "").strip()
    if not configured:
        try:
            from .config import plugin_config

            configured = (plugin_config.pokemon_data_dir or "").strip()
        except Exception:
            configured = ""
    if configured:
        path = Path(configured).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        return path.resolve()

    try:  # 可选依赖：localstore
        from nonebot_plugin_localstore import get_plugin_data_dir  # type: ignore

        path = Path(get_plugin_data_dir())
        path.mkdir(parents=True, exist_ok=True)
        return path.resolve()
    except Exception:
        pass

    path = Path.cwd() / "data" / "pokemon"
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def pokemon_data_dir() -> Path:
    path = data_root() / "Pokemon"
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_dir() -> Path:
    path = data_root() / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def web_dir() -> Path:
    return data_root() / "web"


__all__ = [
    "PACKAGE_DIR",
    "STATIC_DIR",
    "cache_dir",
    "data_root",
    "pokemon_data_dir",
    "web_dir",
]

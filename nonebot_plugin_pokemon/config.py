"""插件配置。所有字段均有安全默认值，未配置时插件仍可加载。

NoneBot2 会按 ``POKEMON_*`` 环境变量读取这里的字段（pydantic 大小写不敏感）。
"""

from __future__ import annotations

from typing import Literal

from nonebot import get_plugin_config
from pydantic import BaseModel, Field


class Config(BaseModel):
    """Pokemon NoneBot2 分支配置。"""

    # ---------------------------------------------------------------- 通用
    pokemon_enabled: bool = True
    pokemon_command_prefixes: list[str] = Field(default_factory=list)
    pokemon_data_dir: str = ""

    # ---------------------------------------------------------------- 资源
    pokemon_resource_base_url: str = "https://silverwing.elysia.beauty/Pokemon"
    pokemon_resource_auto_download: bool = True
    pokemon_resource_download_concurrency: int = 8

    # ---------------------------------------------------------------- 网页
    pokemon_web_enabled: bool = True
    pokemon_web_path: str = "/pokemon"
    pokemon_qweb_enabled: bool = True
    pokemon_qweb_path: str = "/qweb/pokemon"
    pokemon_qweb_admin_path: str = "/qweb/admin/pokemon"
    pokemon_qweb_user_header: str = "X-QWeb-User-Id"
    pokemon_qweb_name_header: str = "X-QWeb-User-Name"
    pokemon_qweb_admin_header: str = "X-QWeb-Is-Admin"
    pokemon_qweb_secret: str = ""
    pokemon_web_allow_guest: bool = True
    pokemon_web_default_user: str = "web-guest"

    # ---------------------------------------------------------------- LLM
    pokemon_llm_enabled: bool = True
    pokemon_llm_provider: Literal["auto", "openai", "moellmchats", "off"] = "auto"
    pokemon_llm_base_url: str = ""
    pokemon_llm_api_key: str = ""
    pokemon_llm_model: str = "gpt-4o-mini"
    pokemon_llm_timeout: float = 90.0
    pokemon_llm_max_steps: int = 6
    pokemon_llm_temperature: float = 0.4

    # ---------------------------------------------------------------- 行为
    pokemon_interaction_timeout: float = 60.0


def _load_config() -> Config:
    """NoneBot 初始化后读取真实配置；离线导入/单测时使用默认值。"""

    try:
        return get_plugin_config(Config)
    except Exception:
        return Config()


plugin_config: Config = _load_config()

__all__ = ["Config", "plugin_config"]

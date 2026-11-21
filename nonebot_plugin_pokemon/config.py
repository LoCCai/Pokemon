"""插件配置。所有字段均有安全默认值，未配置时插件仍可加载。

NoneBot2 会按 ``POKEMON_*`` 环境变量读取这里的字段（pydantic 大小写不敏感）。

七七分支不保存任何模型/密钥/供应商配置：AI 能力只通过 MoEllmChats 的
ToolSpec 暴露，模型由宿主 ``/qweb/chat`` 里用户选择的 New API 模型决定。
网页默认关闭，接入真实 QWeb 宿主后再显式开启。
"""

from __future__ import annotations

from pydantic import BaseModel, Field, SecretStr


class Config(BaseModel):
    """Pokemon NoneBot2 (qiqi) 分支配置。"""

    # ---------------------------------------------------------------- 通用
    pokemon_enabled: bool = True
    pokemon_command_prefixes: list[str] = Field(default_factory=list)
    pokemon_data_dir: str = ""

    # ---------------------------------------------------------------- 存储
    # 默认 SQLite 独立兼容；七七生产显式 POKEMON_STORAGE=postgres。
    # 测试/standalone 可显式 POKEMON_DATABASE_URL；生产留空时复用宿主
    # src.qi_web.config.get_settings().database_url。DSN 不写日志。
    pokemon_storage: str = "sqlite"
    pokemon_database_url: SecretStr = SecretStr("")

    # ---------------------------------------------------------------- 资源
    pokemon_resource_base_url: str = "https://silverwing.elysia.beauty/Pokemon"
    pokemon_resource_auto_download: bool = True
    pokemon_resource_download_concurrency: int = 8

    # ---------------------------------------------------------------- 网页 / QWeb
    # 默认关闭。只有宿主提供 src.qi_web.dependencies 的三个认证依赖时才建议开启；
    # 离线测试可以通过 setup_web(auth=...) / create_router(auth) 注入。
    pokemon_web_enabled: bool = False
    pokemon_qweb_enabled: bool = True
    pokemon_qweb_path: str = "/qweb/pokemon"
    pokemon_qweb_admin_path: str = "/qweb/admin/pokemon"

    # ---------------------------------------------------------------- 行为
    pokemon_interaction_timeout: float = 60.0


def _load_config() -> Config:
    """NoneBot 初始化后读取真实配置；离线导入/单测时使用默认值。"""

    try:
        from nonebot import get_plugin_config

        return get_plugin_config(Config)
    except Exception:
        return Config()


plugin_config: Config = _load_config()

__all__ = ["Config", "plugin_config"]
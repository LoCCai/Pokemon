"""NoneBot2 宝可梦插件入口。

* 游戏核心沿用上游实现，通过 :mod:`nonebot_plugin_pokemon.compat` 适配；
* 单条统一 Matcher 分发约 140 个触发词，覆盖 OneBot v11 / v12 / QQ 官方机器人；
* 菜单、QWeb 与 MoEllmChats 工具共用 :mod:`nonebot_plugin_pokemon.menu.catalog` 的目录；
* 网页只接宿主 ``src.qi_web.dependencies`` 的认证，不再内置直连模型 Agent。
"""

from __future__ import annotations

from nonebot import get_driver
from nonebot.plugin import PluginMetadata

from .config import Config, plugin_config
from .menu import VERSION, menu_data

QIQI_CHAT_TOOLS = True

# 导入即注册全部游戏指令（顺序与上游一致）
from .Pokemon import pokemon_duel as _pokemon_duel  # noqa: F401
from .Pokemon import pokemon_resource as _pokemon_resource  # noqa: F401
from .Pokemon import pokemon_whois as _pokemon_whois  # noqa: F401
from .matchers.dispatcher import register_matcher

__plugin_meta__ = PluginMetadata(
    name="宝可梦",
    description=(
        "宝可梦养成 / 探索 / 对战 / 道具 / 小游戏。支持 OneBot v11、OneBot v12、"
        "QQ 官方机器人，以及 PicMenu Next 菜单、MoEllmChats 工具调用与 QWeb 网页游玩。"
    ),
    usage=(
        "发送 `宝可梦帮助` 查看主指令；发送 `领取初始精灵 小火龙` 开局。"
        "QWeb 入口 `/qweb/pokemon` 需宿主认证；网页默认关闭，由宿主显式开启。"
    ),
    type="application",
    config=Config,
    supported_adapters={"~onebot.v11", "~onebot.v12", "~qq"},
    extra={
        "author": "jiluoQAQ / LoCCai",
        "version": VERSION,
        "menu_data": menu_data(),
        "pmn": {
            "hidden": False,
            "markdown": True,
            "template": None,
            "inherit_func_template": True,
        },
    },
)

try:
    if plugin_config.pokemon_enabled:
        register_matcher()
except Exception:  # 离线导入时不注册 Matcher
    pass

try:
    _driver = get_driver()
except Exception:  # 离线导入（单测/工具脚本）时没有 NoneBot driver
    _driver = None

_started = False

if _driver is not None:

    @_driver.on_startup
    async def _pokemon_startup() -> None:
        global _started
        if _started or not plugin_config.pokemon_enabled:
            return

        from .compat.aps import scheduler
        from .compat.logger import logger
        from .menu import write_external_menu
        from .resources.downloader import start_worker

        from .Pokemon.utils.dbbase.storage import verify_schema

        await verify_schema()
        _started = True
        scheduler.start()
        start_worker()

        try:
            from nonebot import get_bots

            from .platform.ingress import adapter_kind_of_bot
            from .platform.sender import register_proactive

            for bot in get_bots().values():
                register_proactive(bot, adapter_kind_of_bot(bot))
        except Exception:
            pass
        try:
            path = write_external_menu()
            logger.debug(f"[pokemon] 已写入 PicMenu 外部菜单: {path}")
        except Exception as exc:
            logger.debug(f"[pokemon] 写入 PicMenu 外部菜单失败: {exc}")

        try:
            from .web.app import setup_web

            setup_web()
        except Exception as exc:
            logger.warning(f"[pokemon] 网页模块初始化失败: {exc}")

        try:
            from .llm.integration import setup_llm_tools

            setup_llm_tools()
        except Exception as exc:
            logger.warning(f"[pokemon] LLM 工具注册失败: {exc}")

    @_driver.on_shutdown
    async def _pokemon_shutdown() -> None:
        from .compat.aps import scheduler
        from .platform.interaction import broker

        broker.clear()
        await scheduler.shutdown()
        try:
            from .Pokemon.utils.dbbase.storage import close_storage

            await close_storage()
        except Exception:
            pass

    @_driver.on_bot_connect
    async def _pokemon_bot_connect(bot) -> None:
        from .platform.ingress import adapter_kind_of_bot
        from .platform.sender import register_proactive

        register_proactive(bot, adapter_kind_of_bot(bot))


__all__ = ["__plugin_meta__"]

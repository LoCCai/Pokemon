"""MoEllmChats 强类型 ToolSpec 接入（可选依赖）。

* 未安装 ``nonebot_plugin_moellmchats`` 时完全跳过，不影响插件加载；
* 注册的工具与 QWeb/宿主工具桥共用 :mod:`nonebot_plugin_pokemon.llm.tools`；
* 变更型 ``pokemon_command`` 交给 MoEllmChats 的二阶段确认。
"""

from __future__ import annotations

from typing import Any

from ..compat.logger import logger
from .tools import TOOLS, ToolDef, execute_tool

_REGISTERED = False


def _make_handler(tool: ToolDef):
    async def handler(_tool_context: Any = None, **kwargs: Any) -> Any:
        from nonebot_plugin_moellmchats import ToolResult  # type: ignore

        if tool.effect == "mutating" and getattr(_tool_context, "confirmed", False) is not True:
            return ToolResult(text="该操作需要宿主确认。", metadata={"requires_confirmation": True})
        outcome = await execute_tool(tool.name, kwargs, _tool_context)
        result_kwargs: dict[str, Any] = {
            "text": outcome.text[: tool.result_limit],
            "images": tuple(outcome.images),
        }
        if outcome.structured:
            result_kwargs["structured"] = outcome.structured
        if outcome.metadata:
            result_kwargs["metadata"] = outcome.metadata
        return ToolResult(**result_kwargs)

    handler.__name__ = f"pokemon_tool_{tool.name}"
    return handler


def register() -> bool:
    """把全部工具注册到 MoEllmChats（幂等）。"""

    global _REGISTERED
    if _REGISTERED:
        return True
    try:
        from nonebot_plugin_moellmchats import (  # type: ignore
            ToolEffect,
            ToolSpec,
            register_tool,
        )
        from nonebot_plugin_moellmchats.tool_contracts import tool_registry  # type: ignore
    except Exception:
        logger.debug("[pokemon] 未安装 nonebot-plugin-moellmchats，跳过 ToolSpec 注册")
        return False

    specs = []
    for tool in TOOLS:
        effect = ToolEffect.MUTATING if tool.effect == "mutating" else ToolEffect.READ_ONLY
        specs.append(
            ToolSpec(
                name=tool.name,
                description=tool.description,
                parameters=tool.parameters,
                handler=_make_handler(tool),
                effect=effect,
                permission="user",
                timeout_seconds=tool.timeout,
                result_limit=tool.result_limit,
            )
        )

    try:
        if any(tool_registry.get(spec.name) is not None for spec in specs):
            logger.warning("[pokemon] MoEllmChats 工具名已被占用，保留原工具并跳过注册")
            return False
        for spec in specs:
            register_tool(spec)
    except Exception as exc:
        logger.warning(f"[pokemon] 注册 MoEllmChats 工具失败: {exc}")
        return False

    _REGISTERED = True
    logger.info(f"[pokemon] 已向 MoEllmChats 注册 {len(specs)} 个宝可梦工具")
    return True


def unregister() -> None:
    global _REGISTERED
    if not _REGISTERED:
        return
    try:
        from nonebot_plugin_moellmchats.tool_contracts import tool_registry  # type: ignore

        for tool in TOOLS:
            tool_registry.unregister(tool.name)
    except Exception:
        pass
    _REGISTERED = False


def setup_llm_tools() -> bool:
    return register()


__all__ = ["register", "setup_llm_tools", "unregister"]

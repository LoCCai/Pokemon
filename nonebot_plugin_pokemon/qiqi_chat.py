"""QWeb personal chat tools. Identity and confirmation come from the host.

主控负责把宿主 ``account`` 接到这里的 ``qq`` / ``role``。本模块本身不是 HTTP
路由，不读取请求头；``is_admin`` 仅为旧调用兼容，角色优先，管理员始终由角色
推导。变更型工具必须由宿主二阶段确认后传 ``confirmed=True``。
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from .config import plugin_config
from .identity import effective_role
from .llm.tools import TOOL_MAP, ToolContextData, execute_tool


def definitions() -> Dict[str, Any]:
    if not (plugin_config.pokemon_enabled and plugin_config.pokemon_qweb_enabled):
        return {}
    return TOOL_MAP


async def call(
    name: str,
    arguments: Dict[str, Any],
    *,
    qq: str,
    thread: str = "",
    role: str = "",
    is_admin: bool = False,
    confirmed: bool = False,
) -> Tuple[str, Dict[str, Any], list]:
    tool = definitions().get(name)
    if tool is None:
        raise ValueError(f"未知宝可梦工具：{name}")
    qq = str(qq or "").strip()
    if not qq:
        raise ValueError("缺少宿主绑定的 QQ")
    fixed_role = effective_role(role, is_admin=is_admin)
    if tool.effect == "mutating" and not confirmed:
        raise ValueError("变更型操作需要用户确认")
    arguments = dict(arguments or {})

    if name == "pokemon_command":
        from .web.session import registry

        command = str(arguments.get("command") or "").strip()
        if not command:
            raise ValueError("指令为空")
        session = registry.get(qq, None, qq, is_admin=False, role=fixed_role)
        result = await registry.submit(session, command)
        if not result["ok"]:
            raise ValueError(result["error"])
        text = result["text"]
        if choices := result["buttons"]:
            text += "\n可选操作：" + " / ".join(str(c["data"]) for c in choices[:12])
        if result["awaiting"] or not result["done"]:
            text += "\n可在宝可梦页面继续当前指令。"
        return text, {}, [("宝可梦", "image", image) for image in result["images"]]

    ctx = ToolContextData(user_id=qq, platform="qweb", role=fixed_role)
    result = await execute_tool(name, arguments, ctx)
    return result.text, result.structured, [("宝可梦", "image", image) for image in result.images]
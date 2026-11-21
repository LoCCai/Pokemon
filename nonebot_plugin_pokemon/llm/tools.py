"""LLM 工具定义（MoEllmChats ToolSpec 与 QWeb 工具桥共用）。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from ..compat.logger import logger
from ..identity import effective_role, event_is_admin, event_role, is_admin_role, normalized_role


@dataclass
class ToolContextData:
    """工具执行上下文。

    ``is_admin`` 只是角色推导结果；调用方不得用客户端字段直接设置管理员。
    """

    user_id: str = ""
    group_id: Optional[str] = None
    user_name: str = ""
    is_admin: bool = False
    platform: str = "web"
    role: str = "member"

    def __post_init__(self) -> None:
        self.role = effective_role(self.role, is_admin=self.is_admin)
        self.is_admin = is_admin_role(self.role)


@dataclass
class ToolOutcome:
    text: str = ""
    structured: Dict[str, Any] = field(default_factory=dict)
    images: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolDef:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable[..., Any]
    effect: str = "read_only"  # read_only / mutating
    timeout: float = 30.0
    result_limit: int = 6000


def resolve_context(raw: Any) -> ToolContextData:
    """把宿主/聊天工具上下文归一化为可信身份。

    * 普通 dict 只接受 ``user_id`` / ``group_id`` / ``user_name`` / ``role``；
      显式 ``is_admin`` / ``platform`` 会被丢弃，角色再推导管理员。
    * 任意对象只读取身份字段和 ``role``，不读取 ``is_admin``。
    * 聊天事件按发送者角色推导；不再用 ``user_pm`` 直接授予工具管理员。
    """

    if isinstance(raw, ToolContextData):
        return ToolContextData(
            user_id=raw.user_id,
            group_id=raw.group_id,
            user_name=raw.user_name,
            is_admin=raw.is_admin,
            platform=raw.platform,
            role=raw.role,
        )
    if isinstance(raw, dict):
        role = normalized_role(raw.get("role"))
        return ToolContextData(
            user_id=str(raw.get("user_id") or ""),
            group_id=raw.get("group_id"),
            user_name=str(raw.get("user_name") or ""),
            is_admin=is_admin_role(role),
            platform="web",
            role=role,
        )
    if raw is None:
        return ToolContextData()
    event = getattr(raw, "event", None)
    if event is not None and (getattr(raw, "user_id", None) is None or hasattr(raw, "bot")):
        try:
            from ..platform.ingress import to_event

            ev = to_event(getattr(raw, "bot", None), event)
            if ev is not None:
                return ToolContextData(
                    user_id=ev.user_id,
                    group_id=ev.group_id,
                    user_name=str(ev.sender.get("nickname") or ev.user_id),
                    is_admin=event_is_admin(ev),
                    platform=ev.platform,
                    role=event_role(ev),
                )
        except Exception:
            pass
    return ToolContextData(
        user_id=str(getattr(raw, "user_id", None) or ""),
        group_id=getattr(raw, "group_id", None),
        user_name=str(getattr(raw, "user_name", None) or ""),
        is_admin=False,
        platform=str(getattr(raw, "platform", None) or "web"),
        role=normalized_role(getattr(raw, "role", None)),
    )


def _json_schema(properties: Dict[str, Any], required: Optional[List[str]] = None) -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }


# --------------------------------------------------------------------------- handlers
def _identity_required(_ctx: ToolContextData, action: str) -> Optional[ToolOutcome]:
    if not _ctx.user_id:
        return ToolOutcome(text=f"未识别当前用户身份，无法{action}。")
    return None


async def _help_search(*, query: str = "", _ctx: ToolContextData) -> ToolOutcome:
    from ..menu.catalog import search_entries

    entries = search_entries(query)[:12]
    if not entries:
        return ToolOutcome(text=f"没有找到与“{query}”相关的宝可梦功能。")
    lines = [f"- {e['func']}：{e['brief_des']} 触发：{e['trigger_method']}" for e in entries]
    return ToolOutcome(
        text="宝可梦功能：\n" + "\n".join(lines),
        structured={"entries": entries},
    )


async def _profile(*, _ctx: ToolContextData) -> ToolOutcome:
    from ..game import repository

    if missing := _identity_required(_ctx, "查询档案"):
        return missing
    data = await repository.profile(_ctx.user_id)
    team_lines = [
        f"{m['name']} Lv.{m['level']} ({'/'.join(m['types'])})" for m in data.get("team", [])
    ]
    text = (
        f"训练家 {data['nickname']}：金币 {data['score']}，声望 {data['reputation']}，"
        f"拥有 {data['pokemon_count']} 只宝可梦，当前在 {data.get('region', '')}-{data.get('map', '')}。"
    )
    if team_lines:
        text += "\n出战队伍：" + "；".join(team_lines)
    else:
        text += "\n尚未设置出战队伍。"
    return ToolOutcome(text=text, structured=data)


async def _owned(*, page: int = 1, _ctx: ToolContextData) -> ToolOutcome:
    from ..game import repository

    if missing := _identity_required(_ctx, "查询宝可梦"):
        return missing
    data = await repository.owned(_ctx.user_id, max(0, int(page) - 1))
    if not data["items"]:
        return ToolOutcome(text="你还没有宝可梦，先发送 `领取初始精灵 小火龙` 开局。", structured=data)
    lines = [
        f"{item['name']} Lv.{item['level']} {'/'.join(item['types'])}"
        + (" ★" if item.get("star") == 1 else "")
        + (" ◆" if item.get("star") == 2 else "")
        for item in data["items"]
    ]
    return ToolOutcome(
        text=f"共 {data['total']} 只，当前第 {page} 页：\n" + "\n".join(lines),
        structured=data,
    )


async def _dex(*, name: str, _ctx: ToolContextData) -> ToolOutcome:
    from ..game.data import dex_entry

    data = dex_entry(name)
    if not data:
        return ToolOutcome(text=f"没有找到宝可梦“{name}”。")
    stats = "，".join(f"{k} {v}" for k, v in data["base_stats"].items())
    text = (
        f"{data['name']}（#{data['id']}，{'/'.join(data['types'])}）\n"
        f"种族值：{stats}，总和 {data['base_total']}\n"
        f"图鉴：{data['description']}\n"
        f"可学技能：{'、'.join(item['move'] for item in data['learnset'][:20]) or '无'}"
    )
    return ToolOutcome(text=text, structured=data)


async def _move(*, name: str, _ctx: ToolContextData) -> ToolOutcome:
    from ..game.data import move_entry

    data = move_entry(name)
    if not data:
        return ToolOutcome(text=f"没有找到技能“{name}”。")
    return ToolOutcome(
        text=(
            f"{data['name']}：{data['type']} / {data['damage_class']}，威力 {data['power']}，"
            f"命中 {data['accuracy']}，PP {data['pp']}\n{data['description']}"
        ),
        structured=data,
    )


async def _item(*, name: str, _ctx: ToolContextData) -> ToolOutcome:
    from ..game.data import item_entry

    data = item_entry(name)
    if not data:
        return ToolOutcome(text=f"没有找到道具“{name}”。")
    return ToolOutcome(
        text=f"{data['name']}（{data.get('type', '')}）：{data.get('content', '')}，商店价 {data.get('score', '?')}",
        structured=data,
    )


async def _type_chart(*, attack_type: str, defender_types: List[str], _ctx: ToolContextData) -> ToolOutcome:
    from ..game.data import type_effectiveness

    multiplier = type_effectiveness(attack_type, defender_types)
    return ToolOutcome(
        text=f"{attack_type} 对 {'/'.join(defender_types)} 的倍率是 x{multiplier:g}。",
        structured={"attack_type": attack_type, "defender_types": defender_types, "multiplier": multiplier},
    )


async def _team_analysis(*, _ctx: ToolContextData) -> ToolOutcome:
    from ..game import repository
    from ..game.analytics import recommendations, team_analysis

    if missing := _identity_required(_ctx, "分析队伍"):
        return missing
    profile = await repository.profile(_ctx.user_id)
    analysis = team_analysis(profile.get("team", []))
    tips = recommendations(analysis)
    text = (
        f"队伍 {analysis['team_size']} 只，属性覆盖 {analysis['unique_types']} 种。\n"
        + "\n".join(f"- {tip}" for tip in tips)
    )
    return ToolOutcome(
        text=text,
        structured={"profile": profile, "analysis": analysis, "recommendations": tips},
    )


async def _global_overview(*, _ctx: ToolContextData) -> ToolOutcome:
    from ..game.analytics import global_overview

    data = await global_overview()
    top = "、".join(f"{item['name']}({item['count']})" for item in data["top_species"][:5])
    return ToolOutcome(
        text=(
            f"全服 {data['players']} 名训练家，{data['pokemon_records']} 条宝可梦记录，"
            f"平均等级 {data['average_level']}。热门：{top}。"
        ),
        structured=data,
    )


async def _leaderboard(*, kind: str = "score", _ctx: ToolContextData) -> ToolOutcome:
    from ..game import repository

    if kind == "dungeon":
        data = await repository.dungeon_leaderboard()
        lines = [f"{i+1}. {item['uid']} 第 {item['floor']} 层" for i, item in enumerate(data)]
    elif kind == "pokedex":
        data = await repository.pokedex_leaderboard()
        lines = [f"{i+1}. {item['uid']} 收集 {item['unique_pokemon']} 种" for i, item in enumerate(data)]
    else:
        data = await repository.score_leaderboard()
        lines = [f"{i+1}. {item['nickname']} 金币 {item['score']}" for i, item in enumerate(data)]
    return ToolOutcome(text="排行榜：\n" + ("\n".join(lines) or "暂无数据"), structured={"items": data})


async def _chart(*, kind: str = "team_radar", _ctx: ToolContextData) -> ToolOutcome:
    from ..game import charts, repository
    from ..game.analytics import global_overview, team_analysis

    team_kinds = {"team_radar", "team_levels", "team_types"}
    if kind in team_kinds and (missing := _identity_required(_ctx, "生成玩家图表")):
        return missing
    profile = await repository.profile(_ctx.user_id) if kind in team_kinds else {}
    if kind in team_kinds:
        analysis = team_analysis(profile.get("team", []))
        images = charts.team_charts(profile, analysis)
    elif kind in {"popular_species", "level_distribution"}:
        images = charts.global_charts(await global_overview())
    else:
        return ToolOutcome(text=f"不支持的图表：{kind}，可用 team_radar / team_levels / team_types / popular_species / level_distribution。")
    data = images.get(kind)
    if not data:
        return ToolOutcome(text="暂无可用于绘图的数据。")
    return ToolOutcome(
        text=f"已生成图表：{kind}",
        images=[charts.to_data_url(data)],
        structured={"kind": kind, "bytes": len(data)},
    )


async def _command(*, command: str, _ctx: ToolContextData) -> ToolOutcome:
    from ..game.runner import run_command

    if missing := _identity_required(_ctx, "执行游戏指令"):
        return missing
    result = await run_command(
        command,
        user_id=_ctx.user_id,
        group_id=_ctx.group_id,
        user_name=_ctx.user_name,
        is_admin=_ctx.is_admin,
        role=_ctx.role,
        timeout=25.0,
        interaction_timeout=6.0,
    )
    if result.denied:
        text = "该指令需要管理员权限。"
    elif not result.matched:
        text = f"没有匹配 `{command}` 的宝可梦指令。"
    else:
        parts = []
        if result.text:
            parts.append(result.text)
        if result.images:
            parts.append(f"[生成了 {len(result.images)} 张图片]")
        if result.buttons:
            parts.append("可选操作：" + " / ".join(b["data"] for b in result.buttons[:12]))
        if result.awaiting:
            parts.append("该指令进入连续交互（战斗/小游戏），请提示用户在网页或聊天中继续操作。")
        if result.error and result.ok:
            parts.append(f"错误：{result.error}")
        text = "\n".join(parts) or "指令已执行，但没有文本输出。"
    return ToolOutcome(
        text=text,
        structured={"command": command, "buttons": result.buttons, "awaiting": result.awaiting},
        images=result.images[:6],
    )


async def _report(*, _ctx: ToolContextData) -> ToolOutcome:
    from ..game import charts, repository
    from ..game.analytics import player_report, recommendations

    if missing := _identity_required(_ctx, "生成训练家报告"):
        return missing
    report = await player_report(_ctx.user_id)
    profile = report["profile"]
    analysis = report["team_analysis"]
    tips = recommendations(analysis)
    images = charts.team_charts(profile, analysis)
    text = (
        f"{profile['nickname']} 的训练家报告\n"
        f"金币 {profile['score']}｜声望 {profile['reputation']}｜宝可梦 {profile['pokemon_count']}｜"
        f"试炼塔 {profile['dungeon_floor']} 层\n"
        + "\n".join(f"- {tip}" for tip in tips)
    )
    return ToolOutcome(
        text=text,
        structured={"report": report, "recommendations": tips},
        images=[charts.to_data_url(data) for data in images.values()],
    )


TOOLS: List[ToolDef] = [
    ToolDef(
        "pokemon_help_search",
        "搜索宝可梦游戏的功能/指令目录。用户问“宝可梦怎么玩/某功能在哪/有哪些指令”时先调用。",
        _json_schema(
            {"query": {"type": "string", "maxLength": 80, "description": "功能关键词，如 对战、道具、初始精灵；留空返回全部"}},
        ),
        _help_search,
    ),
    ToolDef(
        "pokemon_player_profile",
        "查询当前调用者自己的训练家档案、金币、声望、所在地点与出战队伍。只读。",
        _json_schema({}),
        _profile,
    ),
    ToolDef(
        "pokemon_owned_list",
        "分页查询当前调用者拥有的宝可梦、等级、属性与闪光标记。只读。",
        _json_schema(
            {"page": {"type": "integer", "minimum": 1, "maximum": 100, "description": "页码，默认 1"}},
        ),
        _owned,
    ),
    ToolDef(
        "pokemon_dex_lookup",
        "查询宝可梦图鉴：属性、种族值、进化链、可学技能与图鉴描述。只读。",
        _json_schema({"name": {"type": "string", "minLength": 1, "maxLength": 40, "description": "宝可梦名称或图鉴编号"}}, ["name"]),
        _dex,
    ),
    ToolDef(
        "pokemon_move_lookup",
        "查询技能的类型、威力、命中、PP 与效果。只读。",
        _json_schema({"name": {"type": "string", "minLength": 1, "maxLength": 40}}, ["name"]),
        _move,
    ),
    ToolDef(
        "pokemon_item_lookup",
        "查询道具类型、效果与商店价格。只读。",
        _json_schema({"name": {"type": "string", "minLength": 1, "maxLength": 40}}, ["name"]),
        _item,
    ),
    ToolDef(
        "pokemon_type_chart",
        "计算攻击属性对一组防守属性的伤害倍率。只读。",
        _json_schema(
            {
                "attack_type": {"type": "string", "maxLength": 8},
                "defender_types": {
                    "type": "array",
                    "items": {"type": "string", "maxLength": 8},
                    "minItems": 1,
                    "maxItems": 2,
                },
            },
            ["attack_type", "defender_types"],
        ),
        _type_chart,
    ),
    ToolDef(
        "pokemon_team_analysis",
        "分析当前出战队伍的平均能力、属性覆盖、共同弱点并给出补强建议。只读。",
        _json_schema({}),
        _team_analysis,
    ),
    ToolDef(
        "pokemon_global_overview",
        "查看全服玩家数、宝可梦记录、平均等级、热门宝可梦与等级分布。只读。",
        _json_schema({}),
        _global_overview,
    ),
    ToolDef(
        "pokemon_leaderboard",
        "查看金币、图鉴收集或试炼塔排行榜。只读。",
        _json_schema(
            {"kind": {"type": "string", "enum": ["score", "pokedex", "dungeon"], "description": "排行榜类型"}},
        ),
        _leaderboard,
    ),
    ToolDef(
        "pokemon_chart",
        "生成队伍雷达图、等级柱状图、属性分布饼图或全服热门/等级分布图，返回图片。只读。",
        _json_schema(
            {
                "kind": {
                    "type": "string",
                    "enum": ["team_radar", "team_levels", "team_types", "popular_species", "level_distribution"],
                }
            },
            ["kind"],
        ),
        _chart,
    ),
    ToolDef(
        "pokemon_player_report",
        "生成当前玩家的综合报告（档案 + 队伍分析 + 图表）。只读。",
        _json_schema({}),
        _report,
    ),
    ToolDef(
        "pokemon_command",
        "以当前调用者身份执行一条宝可梦游戏指令（如 野外探索、领取初始精灵 小火龙、使用道具）。变更型；需要连续交互的战斗/小游戏请在网页或聊天中继续。",
        _json_schema(
            {"command": {"type": "string", "minLength": 1, "maxLength": 200, "description": "完整游戏指令"}},
            ["command"],
        ),
        _command,
        effect="mutating",
        timeout=40.0,
    ),
]

TOOL_MAP: Dict[str, ToolDef] = {tool.name: tool for tool in TOOLS}


async def execute_tool(name: str, arguments: Dict[str, Any], ctx: Any) -> ToolOutcome:
    tool = TOOL_MAP.get(name)
    if tool is None:
        return ToolOutcome(text=f"未知工具：{name}")
    context = resolve_context(ctx)
    payload = dict(arguments or {})
    payload.pop("_tool_context", None)
    payload.pop("_ctx", None)
    try:
        return await tool.handler(**payload, _ctx=context)
    except TypeError as exc:
        logger.warning(f"[pokemon] 工具 {name} 参数错误: {exc}")
        return ToolOutcome(text=f"工具参数不正确：{exc}")
    except Exception as exc:
        logger.exception(f"[pokemon] 工具 {name} 执行失败: {exc}")
        return ToolOutcome(text=f"工具执行失败：{type(exc).__name__}")


def openai_tool_schemas() -> List[Dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
        for tool in TOOLS
    ]


__all__ = [
    "TOOL_MAP",
    "TOOLS",
    "ToolContextData",
    "ToolDef",
    "ToolOutcome",
    "execute_tool",
    "openai_tool_schemas",
    "resolve_context",
]

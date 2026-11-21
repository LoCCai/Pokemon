"""PicMenu Next 菜单数据与外部菜单文件生成。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .catalog import build_entries, category_index, search_entries

PLUGIN_ID = "nonebot_plugin_pokemon"
PLUGIN_NAME = "宝可梦"
VERSION = "1.0.0"
AUTHOR = "jiluoQAQ / LoCCai"


def menu_data() -> List[Dict[str, Any]]:
    """PluginMetadata.extra["menu_data"]：含 llm_intents 与结构化触发。"""

    result = []
    for entry in build_entries():
        intents = [i for i in entry["llm_intents"] if 4 <= len(i) <= 80][:16]
        if not intents:
            intents = [f"宝可梦{entry['func']}怎么用"[:80]]
        item = {
            "func": f"{entry['func']}",
            "trigger_method": entry["trigger_method"],
            "trigger_condition": entry["trigger_condition"],
            "brief_des": entry["brief_des"],
            "detail_des": entry["detail_des"],
            "pmn_hidden": bool(entry["pmn_hidden"]),
            "llm_intents": intents,
            "pmn_triggers": [
                {
                    "type": "direct" if item["type"] == "fullmatch" else "command",
                    "value": item["value"],
                }
                for item in entry["triggers"]
            ],
        }
        result.append(item)
    return result


def external_menu() -> Dict[str, Any]:
    """PicMenu Next 外部菜单（严格 Schema，不含私有扩展字段）。"""

    funcs = []
    for entry in build_entries():
        funcs.append(
            {
                "func": entry["func"],
                "trigger_method": entry["trigger_method"],
                "trigger_condition": entry["trigger_condition"],
                "brief_des": entry["brief_des"],
                "detail_des": entry["detail_des"],
                "pmn_hidden": bool(entry["pmn_hidden"]),
            }
        )
    return {
        "$schema": "https://raw.githubusercontent.com/lgc-NB2Dev/nonebot-plugin-picmenu-next/refs/heads/master/defs/ExternalPluginInfo.json",
        "name": PLUGIN_NAME,
        "author": AUTHOR,
        "version": VERSION,
        "description": (
            "宝可梦养成、探索、对战、道具与小游戏。支持 OneBot v11 / v12 / QQ 官方机器人，"
            "并可通过网页与 AI 游玩。"
        ),
        "usage": "发送 `宝可梦帮助` 查看主指令；发送 `领取初始精灵 小火龙` 开局。",
        "funcs": funcs,
        "pmn": {"hidden": False, "markdown": True, "template": None, "inherit_func_template": True},
        "supported_adapters": ["~onebot.v11", "~onebot.v12", "~qq"],
    }


def external_menu_path() -> Path:
    """优先使用 PicMenu Next 实际配置的 external_infos 目录。"""

    candidates: List[Path] = []
    try:
        from nonebot import get_plugin

        if get_plugin("nonebot_plugin_picmenu_next") is not None:
            from nonebot_plugin_picmenu_next.config import external_infos_dir  # type: ignore

            candidates.append(Path(external_infos_dir))
    except Exception:
        pass
    try:
        from nonebot_plugin_localstore import get_plugin_data_dir  # type: ignore

        try:
            candidates.append(Path(get_plugin_data_dir("nonebot_plugin_picmenu_next")) / "external_infos")
        except TypeError:
            candidates.append(Path(get_plugin_data_dir()) / "external_infos")
    except Exception:
        pass
    candidates.append(Path.cwd() / "data" / "picmenu_next" / "external_infos")
    candidates.append(Path.cwd() / "config" / "nonebot_plugin_picmenu_next" / "external_infos")
    for path in candidates:
        try:
            path.mkdir(parents=True, exist_ok=True)
            return path
        except Exception:
            continue
    return Path.cwd() / "data" / "picmenu_next" / "external_infos"


def write_external_menu() -> Path:
    path = external_menu_path() / f"{PLUGIN_ID}.json"
    path.write_text(
        json.dumps(external_menu(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def help_cards() -> List[Dict[str, Any]]:
    """网页/LLM 使用的分类卡片。"""

    cards = []
    for category, entries in category_index().items():
        cards.append(
            {
                "category": category,
                "count": len(entries),
                "items": [
                    {
                        "func": e["func"],
                        "brief": e["brief_des"],
                        "trigger": e["trigger_method"],
                        "hidden": e["pmn_hidden"],
                    }
                    for e in entries
                ],
            }
        )
    return cards


__all__ = [
    "PLUGIN_ID",
    "PLUGIN_NAME",
    "VERSION",
    "author",
    "build_entries",
    "external_menu",
    "external_menu_path",
    "help_cards",
    "menu_data",
    "search_entries",
    "write_external_menu",
]

author = AUTHOR

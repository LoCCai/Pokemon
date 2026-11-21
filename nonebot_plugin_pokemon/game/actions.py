"""Typed allow-list for QWeb gameplay actions.

Every mutation is translated here into one of the *real* registered core game
handlers. Client supplied text is never executed as a command. Names/regions/
destinations/items are resolved against the real game data and replaced with
their canonical spelling before the handler is invoked.

No database schema, no formulas and no separate game loop live in this module.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..Pokemon.pokemon_duel.map import didianlist, diqulist
from ..Pokemon.pokemon_duel.pmconfig import chushi_list
from ..Pokemon.pokemon_duel.prop import proplist
from ..Pokemon.utils.dbbase.storage import fetchall
from .data import display_name, resolve_pokemon

ALLOWED_ACTIONS = (
    "claim",
    "choose_region",
    "travel",
    "explore",
    "fish",
    "challenge",
    "party",
    "equip",
    "reply",
    "cancel",
)

# Starter families are the real pmconfig.chushi_list entries; region keys come
# from map.json. The list is intentionally explicit: no user input chooses it.
_STARTER_REGION = {
    1: "关东",
    4: "关东",
    7: "关东",
    152: "城都",
    155: "城都",
    158: "城都",
    252: "丰缘",
    255: "丰缘",
    258: "丰缘",
    387: "神奥",
    390: "神奥",
    393: "神奥",
    495: "合众",
    498: "合众",
    501: "合众",
    650: "卡洛斯",
    653: "卡洛斯",
    656: "卡洛斯",
    722: "阿罗拉",
    725: "阿罗拉",
    728: "阿罗拉",
    810: "伽勒尔",
    813: "伽勒尔",
    816: "伽勒尔",
    906: "帕底亚",
    909: "帕底亚",
    912: "帕底亚",
}

_CHALLENGES: Dict[str, Tuple[str, str]] = {
    "gym": ("挑战道馆", "道馆"),
    "道馆": ("挑战道馆", "道馆"),
    "挑战道馆": ("挑战道馆", "道馆"),
    "elite": ("挑战天王", "天王"),
    "elite_four": ("挑战天王", "天王"),
    "天王": ("挑战天王", "天王"),
    "四天王": ("挑战天王", "天王"),
    "挑战天王": ("挑战天王", "天王"),
    "champion": ("挑战四天王冠军", "冠军"),
    "冠军": ("挑战四天王冠军", "冠军"),
    "四天王冠军": ("挑战四天王冠军", "冠军"),
    "挑战冠军": ("挑战四天王冠军", "冠军"),
    "挑战四天王冠军": ("挑战四天王冠军", "冠军"),
    "boss": ("首领挑战", "首领"),
    "首领": ("首领挑战", "首领"),
    "首领挑战": ("首领挑战", "首领"),
    "world_boss": ("世界boss挑战", "世界首领"),
    "worldboss": ("世界boss挑战", "世界首领"),
    "世界首领": ("世界boss挑战", "世界首领"),
    "世界boss": ("世界boss挑战", "世界首领"),
    "tower": ("挑战试炼塔", "试炼塔"),
    "试炼塔": ("挑战试炼塔", "试炼塔"),
    "精灵塔": ("挑战试炼塔", "试炼塔"),
    "挑战试炼塔": ("挑战试炼塔", "试炼塔"),
    "挑战精灵塔": ("挑战试炼塔", "试炼塔"),
}


class ActionError(ValueError):
    """A safe, user-facing rejection for an invalid action/value."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def normalize_region(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        raise ActionError("请选择初始地区。")
    if text in diqulist:
        key = text
    else:
        key = ""
        for region_key, info in diqulist.items():
            if text in {str(info.get("name") or ""), str(info.get("chushi") or "")}:
                key = region_key
                break
    if not key:
        raise ActionError("地图上没有该地区，请输入正确的地区名称。")
    if int(diqulist[key].get("open", 0)) != 1:
        raise ActionError("当前地区暂未开放，请先前往其他地区冒险。")
    return key


def normalize_destination(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        raise ActionError("请选择目的地。")
    if text not in didianlist:
        raise ActionError("地图上没有该地点，请输入正确的地址名称。")
    return text


def normalize_starter(value: Any) -> int:
    pid = resolve_pokemon(value)
    if not pid:
        raise ActionError("请输入正确的初始宝可梦名称或编号。")
    if pid not in chushi_list:
        raise ActionError(f"{display_name(pid)}不属于初始精灵，无法领取。")
    return pid


def normalize_item(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        raise ActionError("请选择道具。")
    if text in proplist:
        return text
    for name, info in proplist.items():
        if str(info.get("name") or "") == text:
            return name
    raise ActionError("无法找到该道具，请输入正确的道具名称。")


def normalize_owned_pokemon(value: Any, owned_ids: Sequence[int]) -> int:
    pid = resolve_pokemon(value)
    if not pid:
        raise ActionError("请输入正确的宝可梦名称或编号。")
    if int(pid) not in {int(item) for item in owned_ids}:
        raise ActionError(f"您还没有{display_name(pid)}。")
    return int(pid)


async def owned_ids(uid: str) -> List[int]:
    rows = await fetchall("select bianhao from pokemon_table where uid=?", (uid,))
    return [int(row[0]) for row in rows]


def _party_members(value: Any) -> List[Any]:
    if isinstance(value, (list, tuple)):
        return [item for item in value if str(item or "").strip()]
    text = str(value or "").replace(",", " ").replace("，", " ").split()
    if not text:
        raise ActionError("请选择要编入队伍的宝可梦。")
    return text


def _equip_pair(value: Any) -> Tuple[str, Optional[str]]:
    """Return ``(pokemon, item)``; ``item=None`` means take the item off."""

    if isinstance(value, dict):
        pokemon = value.get("pokemon") or value.get("name") or value.get("mon")
        item = value.get("item") or value.get("prop")
        remove = bool(value.get("remove"))
        if remove:
            item = None
        if not pokemon:
            raise ActionError("请选择宝可梦。")
        if not item:
            return str(pokemon), None
        return str(pokemon), str(item)
    if isinstance(value, (list, tuple)):
        if len(value) != 2:
            raise ActionError("equip 需要 [道具, 宝可梦] 或 [宝可梦, 道具]。")
        first, second = str(value[0] or "").strip(), str(value[1] or "").strip()
        if first in proplist and resolve_pokemon(second):
            return second, first
        if second in proplist and resolve_pokemon(first):
            return first, second
        raise ActionError("无法识别 equip 的道具与宝可梦。")
    parts = str(value or "").split()
    if len(parts) == 1:
        return parts[0], None
    if len(parts) == 2:
        first, second = parts
        if first in proplist and resolve_pokemon(second):
            return second, first
        if second in proplist and resolve_pokemon(first):
            return first, second
        raise ActionError("无法识别 equip 的道具与宝可梦。")
    raise ActionError("equip 的值无法识别。")


def resolve_action(
    action: str,
    value: Any,
    *,
    uid: str,
    owned: Optional[Sequence[int]] = None,
) -> Dict[str, Any]:
    """Translate one allow-listed action into a canonical core command.

    ``reply``/``cancel`` do not produce a command; the session registry handles
    them against the active interaction broker. The return value always contains
    ``action`` and a canonical ``value`` so responses never echo raw client text.
    """

    action = str(action or "").strip()
    if action not in ALLOWED_ACTIONS:
        raise ActionError("不支持的游戏操作。")

    if action == "claim":
        pid = normalize_starter(value)
        return {"action": action, "value": display_name(pid), "id": pid, "command": f"领取初始精灵 {display_name(pid)}"}

    if action == "choose_region":
        region = normalize_region(value)
        return {"action": action, "value": region, "command": f"选择初始地区 {region}"}

    if action == "travel":
        destination = normalize_destination(value)
        return {"action": action, "value": destination, "command": f"前往 {destination}"}

    if action == "explore":
        return {"action": action, "value": None, "command": "野外探索"}

    if action == "fish":
        return {"action": action, "value": None, "command": "野外垂钓"}

    if action == "challenge":
        text = str(value or "").strip()
        if not text:
            raise ActionError("请选择挑战目标（道馆/天王/冠军/首领/世界首领/试炼塔）。")
        normalized = _CHALLENGES.get(text) or _CHALLENGES.get(text.casefold())
        if not normalized:
            raise ActionError("不支持该挑战目标。")
        command, label = normalized
        return {"action": action, "value": label, "command": command}

    if action == "party":
        if owned is None:
            raise ActionError("无法校验队伍成员。", status_code=409)
        members = _party_members(value)
        if len(members) > 6:
            raise ActionError("一个队伍最多只能有6只宝可梦。")
        ids: List[int] = []
        for member in members:
            pid = normalize_owned_pokemon(member, owned)
            if pid not in ids:
                ids.append(pid)
        if not ids:
            raise ActionError("请选择要编入队伍的宝可梦。")
        names = [display_name(pid) for pid in ids]
        return {"action": action, "value": names, "ids": ids, "command": f"更新队伍 {' '.join(names)}"}

    if action == "equip":
        pokemon_raw, item_raw = _equip_pair(value)
        if owned is None:
            raise ActionError("无法校验宝可梦。", status_code=409)
        pid = normalize_owned_pokemon(pokemon_raw, owned)
        name = display_name(pid)
        if not item_raw:
            return {"action": action, "value": {"pokemon": name, "remove": True}, "command": f"取下道具 {name}"}
        item = normalize_item(item_raw)
        return {
            "action": action,
            "value": {"pokemon": name, "item": item},
            "command": f"携带道具 {item} {name}",
        }

    if action == "reply":
        text = str(value or "").strip()
        if not text:
            raise ActionError("回复内容为空。")
        if len(text) > 500:
            raise ActionError("回复内容过长。")
        return {"action": action, "value": text, "command": None}

    if action == "cancel":
        return {"action": action, "value": None, "command": None}

    raise ActionError("不支持的游戏操作。")


def starter_regions() -> Dict[int, str]:
    return dict(_STARTER_REGION)


__all__ = [
    "ALLOWED_ACTIONS",
    "ActionError",
    "normalize_destination",
    "normalize_item",
    "normalize_owned_pokemon",
    "normalize_region",
    "normalize_starter",
    "owned_ids",
    "resolve_action",
    "starter_regions",
]

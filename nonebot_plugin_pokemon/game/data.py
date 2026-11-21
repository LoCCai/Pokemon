"""游戏数据的只读查询层（供网页与 LLM 工具使用）。"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional

from ..Pokemon.pokemon_duel import pokeconfg as pc
from ..Pokemon.pokemon_duel.pokeconfg import (
    CHARA_NAME,
    JINENG_LIST,
    LEVEL_JINENG_LIST,
    POKEMON_CONTENT,
    POKEMON_LIST,
    POKEMON_XUEXI,
    SHUXING_LIST,
    XINGGE_LIST,
    get_poke_bianhao,
    get_pokeon_info,
    get_pokemon_shuxing,
    proplist,
)

TYPE_NAMES = list(SHUXING_LIST.keys())
STAT_NAMES = ["HP", "物攻", "物防", "特攻", "特防", "速度"]


def resolve_pokemon(name_or_id: Any) -> int:
    """名称/别名/编号 -> 图鉴编号；找不到返回 0。"""

    try:
        pid = int(name_or_id)
        if pid in POKEMON_LIST:
            return pid
    except (TypeError, ValueError):
        pass
    text = str(name_or_id or "").strip().replace("）", ")").replace("（", "(")
    for pid, names in CHARA_NAME.items():
        if text in names:
            return int(pid)
    # 忽略大小写/空格的英文名
    folded = text.casefold()
    for pid, names in CHARA_NAME.items():
        if any(str(n).casefold() == folded for n in names):
            return int(pid)
    return 0


def display_name(pid: int) -> str:
    return str(CHARA_NAME.get(pid, [str(pid)])[0])


def types_of(pid: int) -> List[str]:
    raw = POKEMON_LIST.get(pid, [""] * 8)[7]
    return [t for t in re.split(r"[,，]", str(raw)) if t]


def base_stats(pid: int) -> Dict[str, int]:
    row = POKEMON_LIST.get(pid)
    if not row:
        return {}
    return {name: int(row[index]) for index, name in enumerate(STAT_NAMES, start=1)}


def evolution_chain(pid: int) -> List[Dict[str, Any]]:
    chain: List[Dict[str, Any]] = []
    # 向上找前置形态
    current = pid
    seen: set[int] = set()
    while current and current not in seen:
        seen.add(current)
        row = POKEMON_LIST.get(current, [])
        parent = row[8] if len(row) > 8 else "-"
        if str(parent).isdigit() and int(parent):
            current = int(parent)
        else:
            break
    root = current
    # 从根向下展开
    frontier = [root]
    while frontier:
        current = frontier.pop(0)
        row = POKEMON_LIST.get(current, [])
        children = []
        for other, other_row in POKEMON_LIST.items():
            if len(other_row) > 9 and str(other_row[8]) == str(current) and str(other_row[9]) != "-":
                children.append((int(other), str(other_row[9])))
        chain.append(
            {
                "id": int(current),
                "name": display_name(int(current)),
                "types": types_of(int(current)),
                "evolves_to": [{"id": cid, "name": display_name(cid), "condition": cond} for cid, cond in children],
            }
        )
        frontier.extend(cid for cid, _ in children)
    return chain


def dex_entry(name_or_id: Any, *, level: int = 100) -> Optional[Dict[str, Any]]:
    pid = resolve_pokemon(name_or_id)
    if not pid:
        return None
    learnset = []
    for level_req, move in LEVEL_JINENG_LIST.get(pid, []):
        if move in JINENG_LIST:
            learnset.append({"level": int(level_req), "move": move, "type": JINENG_LIST[move][0]})
    return {
        "id": pid,
        "name": display_name(pid),
        "aliases": [str(n) for n in CHARA_NAME.get(pid, [])],
        "types": types_of(pid),
        "base_stats": base_stats(pid),
        "base_total": sum(base_stats(pid).values()),
        "description": (POKEMON_CONTENT.get(pid) or [""])[0],
        "evolution": evolution_chain(pid),
        "learnset": learnset,
        "teachable": list(POKEMON_XUEXI.get(pid, [])),
        "natures": list(XINGGE_LIST.keys()),
    }


def move_entry(name: str) -> Optional[Dict[str, Any]]:
    data = JINENG_LIST.get(name)
    if not data:
        folded = str(name or "").casefold()
        for move_name, move_data in JINENG_LIST.items():
            if move_name.casefold() == folded:
                name, data = move_name, move_data
                break
    if not data:
        return None
    return {
        "name": name,
        "type": data[0],
        "damage_class": data[1],
        "power": data[2],
        "accuracy": data[3],
        "pp": data[4],
        "description": data[5],
        "effect": data[6] if len(data) > 6 else "",
    }


def item_entry(name: str) -> Optional[Dict[str, Any]]:
    data = proplist.get(name)
    if not data:
        for item_name, item_data in proplist.items():
            if item_name == name or item_data.get("name") == name:
                return {"name": item_name, **item_data}
        return None
    return {"name": name, **data}


def type_effectiveness(attack_type: str, defender_types: Iterable[str]) -> float:
    chart = SHUXING_LIST.get(attack_type, {})
    multiplier = 1.0
    for defender in defender_types:
        multiplier *= float(chart.get(defender, 1))
    return multiplier


def type_matrix() -> Dict[str, Dict[str, float]]:
    return {attack: {defend: float(value) for defend, value in row.items()} for attack, row in SHUXING_LIST.items()}


def all_pokemon() -> List[Dict[str, Any]]:
    result = []
    for pid in POKEMON_LIST:
        result.append(
            {
                "id": int(pid),
                "name": display_name(int(pid)),
                "types": types_of(int(pid)),
                "base_total": sum(base_stats(int(pid)).values()),
            }
        )
    return result


async def owned_entry(pid: int, level: int, info, star: int) -> Dict[str, Any]:
    item = {
        "id": pid,
        "name": display_name(pid),
        "level": int(level),
        "star": int(star),
        "types": types_of(pid),
    }
    if info and info != 0:
        stats = await get_pokemon_shuxing(pid, info)
        item.update(
            {
                "nature": info[13],
                "iv": [int(x) for x in info[1:7]],
                "ev": [int(x) for x in info[7:13]],
                "held_item": info[16] or "",
                "moves": [m for m in str(info[14] or "").split(",") if m],
                "stats": dict(zip(STAT_NAMES, [int(x) for x in stats])),
                "exp": int(info[15]),
            }
        )
    return item


async def owned_pokemon(uid: str, page: int = 0, page_size: int = 30) -> Dict[str, Any]:
    total = await pc.POKE._get_pokemon_num(uid)
    rows = await pc.POKE._get_pokemon_list(uid, page)
    if rows == 0:
        rows = []
    items = []
    for bianhao, level in rows[:page_size]:
        pid = int(bianhao)
        info = await get_pokeon_info(uid, pid)
        star = await pc.POKE.get_pokemon_star(uid, pid)
        items.append(await owned_entry(pid, level, info, star))
    return {
        "uid": uid,
        "total": int(total),
        "page": page,
        "page_size": page_size,
        "items": items,
    }


__all__ = [
    "STAT_NAMES",
    "TYPE_NAMES",
    "all_pokemon",
    "base_stats",
    "dex_entry",
    "display_name",
    "evolution_chain",
    "item_entry",
    "move_entry",
    "owned_pokemon",
    "resolve_pokemon",
    "type_effectiveness",
    "type_matrix",
    "types_of",
]

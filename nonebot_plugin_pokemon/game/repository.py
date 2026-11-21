"""训练家档案、队伍、背包与排行榜查询。"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from ..Pokemon.pokemon_duel import pokeconfg as pc
from ..Pokemon.utils.dbbase.storage import fetchall
from .data import display_name, owned_pokemon, types_of


async def _map_row(uid: str) -> List[Any]:
    row = await pc.POKE._get_map_now(uid)
    return list(row) if row else [0, "", 0, 0]


def _region_of(map_name: str) -> str:
    try:
        from ..Pokemon.pokemon_duel.map import didianlist

        info = didianlist.get(map_name)
        if info:
            return str(info.get("fname", ""))
    except Exception:
        pass
    return ""


async def team(uid: str) -> List[Dict[str, Any]]:
    raw = await pc.POKE.get_pokemon_group(uid)
    result: List[Dict[str, Any]] = []
    if not raw:
        return result
    for token in str(raw).split(","):
        token = token.strip()
        if not token:
            continue
        try:
            pid = int(token)
        except ValueError:
            continue
        info = await pc.get_pokeon_info(uid, pid)
        if not info or info == 0:
            continue
        stats = await pc.get_pokemon_shuxing(pid, info)
        result.append(
            {
                "id": pid,
                "name": display_name(pid),
                "level": int(info[0]),
                "types": types_of(pid),
                "nature": info[13],
                "moves": [m for m in str(info[14] or "").split(",") if m],
                "held_item": info[16] or "",
                "iv": [int(x) for x in info[1:7]],
                "ev": [int(x) for x in info[7:13]],
                "stats": dict(zip(["HP", "物攻", "物防", "特攻", "特防", "速度"], [int(x) for x in stats])),
            }
        )
    return result


async def inventory(uid: str) -> Dict[str, Any]:
    props = await pc.POKE.get_pokemon_prop_list(uid)
    eggs = await pc.POKE.get_pokemon_egg_list(uid)
    technical = await pc.POKE.get_pokemon_technical_list(uid, 0)
    if technical and isinstance(technical, (list, tuple)) and len(technical) == 2:
        tech_count, tech_rows = technical
    else:
        tech_count, tech_rows = 0, []
    return {
        "props": [{"name": name, "count": int(num)} for name, num in (props or [])],
        "eggs": [{"id": int(pid), "name": display_name(int(pid)), "count": int(num)} for pid, num in (eggs or [])],
        "technical": [{"name": name, "count": int(num)} for name, num in (tech_rows or [])],
        "technical_total": int(tech_count or 0),
    }


INVENTORY_SOURCES = {
    "eggs": ("pokemon_egg", "bianhao"),
    "items": ("pokemon_prop", "prop"),
    "technical": ("prop_technical", "prop"),
}


async def inventory_page(uid: str, kind: str, page: int = 1) -> Dict[str, Any]:
    """Read one player's inventory page and totals from the same DB snapshot."""
    table, key = INVENTORY_SOURCES[kind]
    size = 30
    rows = await fetchall(
        f"with holdings as (select {key} as item_key, num from {table} where uid=? and num>0), "
        "batch as (select item_key, num from holdings order by num desc, item_key limit ? offset ?), "
        "summary as (select count(*) as kinds, coalesce(sum(num),0) as quantity from holdings) "
        "select summary.kinds, summary.quantity, batch.item_key, batch.num from summary "
        "left join batch on 1=1 order by batch.num desc, batch.item_key",
        (uid, size, (page - 1) * size),
    )
    items = []
    for _, _, item_key, count in rows:
        if item_key is None:
            continue
        if kind == "eggs":
            item = {"id": int(item_key), "name": display_name(int(item_key))}
        else:
            item = {"name": str(item_key)}
        items.append({**item, "count": int(count)})
    return {"kind": kind, "page": page, "page_size": size, "total": int(rows[0][0]),
            "quantity": int(rows[0][1]), "items": items}


async def profile(uid: str) -> Dict[str, Any]:
    map_row = await _map_row(uid)
    score = await pc.SCORE.get_score(uid)
    shengwang = await pc.SCORE.get_shengwang(uid)
    count = await pc.POKE._get_pokemon_num(uid)
    try:
        title = await pc.get_chenghao(uid)
    except Exception:
        title = ""
    try:
        dungeon = await pc.POKE.get_dungeon_info(uid)
    except Exception:
        dungeon = 0
    pipei = await pc.POKE.get_map_pipei_num(uid)
    team_items = await team(uid)
    inv = await inventory(uid)
    return {
        "uid": uid,
        "nickname": map_row[2] or uid,
        "title": title,
        "score": int(score),
        "reputation": int(shengwang),
        "map": map_row[1],
        "badges": int(map_row[0] or 0),
        "region": _region_of(map_row[1]),
        "pokemon_count": int(count),
        "team": team_items,
        "team_size": len(team_items),
        "eggs": inv["eggs"],
        "props": inv["props"],
        "dungeon_floor": int(dungeon),
        "duel_points": int(pipei),
        "auto_explore": bool(map_row[4]) if len(map_row) > 4 else False,
    }


async def owned(uid: str, page: int = 0) -> Dict[str, Any]:
    return await owned_pokemon(uid, page)


async def score_leaderboard(limit: int = 20) -> List[Dict[str, Any]]:
    rows = await fetchall(
        "select s.uid, s.score, s.shengwang, m.nickname from pokemon_score s "
        "left join pokemon_map m on m.uid = s.uid order by s.score desc limit ?",
        (int(limit),),
    )
    return [
        {"uid": row[0], "score": int(row[1]), "reputation": int(row[2]), "nickname": row[3] or row[0]}
        for row in rows
    ]


async def pokedex_leaderboard(limit: int = 20) -> List[Dict[str, Any]]:
    rows = await fetchall(
        "select uid, count(*) as num from pokemon_table group by uid order by num desc limit ?",
        (int(limit),),
    )
    return [{"uid": row[0], "unique_pokemon": int(row[1])} for row in rows]


async def dungeon_leaderboard(limit: int = 20) -> List[Dict[str, Any]]:
    rows = await pc.POKE.get_dungeon_list()
    return [{"uid": row[0], "floor": int(row[1])} for row in (rows or [])][:limit]


async def all_user_ids() -> List[str]:
    rows = await pc.POKE.get_game_user_list()
    if not rows or rows == 0:
        return []
    return [str(row[0] if isinstance(row, (list, tuple)) else row) for row in rows]


__all__ = [
    "all_user_ids",
    "dungeon_leaderboard",
    "inventory",
    "owned",
    "pokedex_leaderboard",
    "profile",
    "score_leaderboard",
    "team",
]

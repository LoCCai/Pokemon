"""Read-only QWeb world projection built from the real saved account/game data."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..Pokemon.pokemon_duel.map import didianlist, diqulist
from ..Pokemon.pokemon_duel.pmconfig import chushi_list
from ..menu import VERSION
from . import repository
from .actions import starter_regions
from ..Pokemon.utils.dbbase.storage import fetchall
from .data import display_name, owned_entry, types_of


def _location(name: str, *, current: str = "") -> Optional[Dict[str, Any]]:
    info = didianlist.get(name)
    if not info:
        return None
    region_key = str(info.get("fname") or "")
    region_info = diqulist.get(region_key) or {}
    return {
        "name": str(info.get("name") or name),
        "region": region_key,
        "region_name": str(region_info.get("name") or region_key),
        "type": str(info.get("type") or ""),
        "need": int(info.get("need") or 0),
        "open": int(region_info.get("open", 1)) == 1,
        "current": name == current,
    }


def regions() -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for key, info in diqulist.items():
        result.append(
            {
                "key": key,
                "name": str(info.get("name") or key),
                "open": int(info.get("open", 0)) == 1,
                "starter": str(info.get("chushi") or ""),
            }
        )
    return result


def starters() -> List[Dict[str, Any]]:
    region_of = starter_regions()
    result: List[Dict[str, Any]] = []
    for pid in chushi_list:
        region = region_of.get(int(pid), "")
        region_info = diqulist.get(region) or {}
        result.append(
            {
                "id": int(pid),
                "name": display_name(int(pid)),
                "types": types_of(int(pid)),
                "region": region,
                "region_name": str(region_info.get("name") or region),
                "open": int(region_info.get("open", 1)) == 1,
                "sprite": f"/api/game/sprite/{int(pid)}",
            }
        )
    return result


def locations() -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for name, info in didianlist.items():
        region_key = str(info.get("fname") or "")
        region_info = diqulist.get(region_key) or {}
        result.append(
            {
                "name": str(info.get("name") or name),
                "region": region_key,
                "region_name": str(region_info.get("name") or region_key),
                "type": str(info.get("type") or ""),
                "need": int(info.get("need") or 0),
                "open": int(region_info.get("open", 1)) == 1,
                "current": False,
            }
        )
    return result


async def _owned_all(uid: str) -> tuple[List[Dict[str, Any]], int]:
    rows = await fetchall(
        "select p.bianhao,coalesce(s.type,0),level,gt_hp,gt_atk,gt_def,gt_stk,gt_sef,gt_spd,"
        "nl_hp,nl_atk,nl_def,nl_stk,nl_sef,nl_spd,xingge,jineng,exp,xiedai "
        "from pokemon_table p left join pokemon_star s on p.uid=s.uid and p.bianhao=s.bianhao "
        "where p.uid=? order by level desc,p.bianhao asc", (uid,),
    )
    items = [await owned_entry(int(pid), int(info[0]), info, int(star)) for pid, star, *info in rows]
    return items, len(items)


async def world(uid: str) -> Dict[str, Any]:
    """Return everything the native QWeb game shell needs for one saved account."""

    profile = await repository.profile(uid)
    owned, owned_total = await _owned_all(uid)
    inv = await repository.inventory(uid)
    current_map = str(profile.get("map") or "")
    current = {
        "started": bool(current_map),
        "map": current_map,
        "region": str(profile.get("region") or ""),
        "location": _location(current_map, current=current_map) if current_map else None,
    }
    location_items = locations()
    for item in location_items:
        item["current"] = item["name"] == current_map
        same_region = item["region"] == current["region"]
        item["open"] = bool(current_map) and profile["badges"] >= (item["need"] if same_region else 8)
    items = [
        {"name": str(item.get("name") or ""), "count": int(item.get("count") or 0), "kind": "prop"}
        for item in (profile.get("props") or [])
    ]
    return {
        "ok": True,
        "version": VERSION,
        "profile": profile,
        "current": current,
        "starters": starters(),
        "owned": owned,
        "owned_total": owned_total,
        "owned_page_size": 30,
        "regions": regions(),
        "locations": location_items,
        "items": items,
        "technical": inv.get("technical") or [],
        "technical_total": int(inv.get("technical_total") or 0),
        "eggs": inv.get("eggs") or [],
        "party": profile.get("team") or [],
        "assets": {
            "sprite": "/api/game/sprite/{id}",
            "fallback": "pokemon-fallback.png",
            "theme": "qweb-theme.js",
            "css": "game.css",
            "js": "game.js",
        },
    }


__all__ = ["locations", "regions", "starters", "world"]

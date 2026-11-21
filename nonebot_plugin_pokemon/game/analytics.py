"""队伍与全服数据分析（纯计算，不写数据库）。"""

from __future__ import annotations

import asyncio
from collections import Counter
from typing import Any, Dict, Iterable, List

import aiosqlite

from ..Pokemon.utils.dbbase.PokeCounter import DB_PATH
from .data import STAT_NAMES, display_name, type_effectiveness, type_matrix, types_of

ALL_TYPES = list(type_matrix().keys())


def _avg(values: Iterable[float]) -> float:
    values = list(values)
    return round(sum(values) / len(values), 2) if values else 0.0


def team_analysis(team_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not team_items:
        return {
            "team_size": 0,
            "average_stats": {},
            "type_coverage": {},
            "weaknesses": [],
            "resistances": [],
            "insights": ["当前没有设置出战队伍。发送 `更新队伍 宝可梦名...` 设置队伍。"],
        }

    stat_keys = ["HP", "物攻", "物防", "特攻", "特防", "速度"]
    averages = {
        key: _avg(item.get("stats", {}).get(key, 0) for item in team_items) for key in stat_keys
    }
    type_counts: Counter = Counter()
    for item in team_items:
        type_counts.update(item.get("types", []))

    weaknesses = []
    resistances = []
    for attack in ALL_TYPES:
        multipliers = [type_effectiveness(attack, item.get("types", [])) for item in team_items]
        weak_count = sum(1 for m in multipliers if m > 1)
        resist_count = sum(1 for m in multipliers if m < 1)
        max_multiplier = max(multipliers) if multipliers else 1
        if weak_count:
            weaknesses.append(
                {
                    "type": attack,
                    "weak_members": weak_count,
                    "max_multiplier": max_multiplier,
                    "severity": round(weak_count * max_multiplier, 2),
                }
            )
        if resist_count:
            resistances.append({"type": attack, "resist_members": resist_count})

    weaknesses.sort(key=lambda item: item["severity"], reverse=True)
    resistances.sort(key=lambda item: item["resist_members"], reverse=True)

    insights: List[str] = []
    if weaknesses:
        top = weaknesses[0]
        insights.append(
            f"队伍最怕 {top['type']} 属性：{top['weak_members']}/{len(team_items)} 只成员被克制（最高 x{top['max_multiplier']}）。"
        )
    if resistances:
        top = resistances[0]
        insights.append(f"队伍对 {top['type']} 的抗性最好：{top['resist_members']} 只成员抵抗。")
    lowest = min(averages, key=averages.get) if averages else ""
    highest = max(averages, key=averages.get) if averages else ""
    if lowest:
        insights.append(f"平均 {lowest} 最低（{averages[lowest]}），建议补充对应定位的宝可梦。")
    if highest:
        insights.append(f"平均 {highest} 最高（{averages[highest]}），可作为队伍主要输出/支点。")
    if len(team_items) < 4:
        insights.append("队伍未满 4 只，建议补齐以覆盖更多属性。")

    return {
        "team_size": len(team_items),
        "average_stats": averages,
        "type_coverage": dict(type_counts),
        "unique_types": len(type_counts),
        "weaknesses": weaknesses[:8],
        "resistances": resistances[:8],
        "insights": insights,
    }


async def global_overview(top_species: int = 10) -> Dict[str, Any]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(DISTINCT UID) FROM POKEMON_MAP WHERE HUIZHANG>0")
        players = (await cursor.fetchone())[0]
        cursor = await db.execute("SELECT COUNT(*), AVG(LEVEL), MAX(LEVEL) FROM POKEMON_TABLE")
        count, avg_level, max_level = await cursor.fetchone()
        cursor = await db.execute(
            "SELECT BIANHAO, COUNT(*) AS NUM, AVG(LEVEL) AS AVGLEVEL FROM POKEMON_TABLE GROUP BY BIANHAO ORDER BY NUM DESC LIMIT ?",
            (int(top_species),),
        )
        species_rows = await cursor.fetchall()
        cursor = await db.execute("SELECT LEVEL, COUNT(*) FROM POKEMON_TABLE GROUP BY LEVEL ORDER BY LEVEL")
        level_rows = await cursor.fetchall()
        cursor = await db.execute("SELECT AVG(SCORE), SUM(SCORE), COUNT(*) FROM POKEMON_SCORE")
        avg_score, total_score, score_users = await cursor.fetchone()

    type_counter: Counter = Counter()
    for pid, num, _ in species_rows:
        for type_name in types_of(int(pid)):
            type_counter[type_name] += int(num)

    return {
        "players": int(players or 0),
        "pokemon_records": int(count or 0),
        "average_level": round(float(avg_level or 0), 2),
        "max_level": int(max_level or 0),
        "average_score": round(float(avg_score or 0), 2),
        "total_score": int(total_score or 0),
        "score_users": int(score_users or 0),
        "top_species": [
            {
                "id": int(pid),
                "name": display_name(int(pid)),
                "count": int(num),
                "average_level": round(float(avg or 0), 2),
            }
            for pid, num, avg in species_rows
        ],
        "level_distribution": [{"level": int(level), "count": int(num)} for level, num in level_rows],
        "type_counts_in_top": dict(type_counter),
    }


async def player_report(uid: str) -> Dict[str, Any]:
    from . import repository

    profile = await repository.profile(uid)
    analysis = team_analysis(profile.get("team", []))
    return {
        "profile": profile,
        "team_analysis": analysis,
        "stat_names": STAT_NAMES,
    }


def recommendations(analysis: Dict[str, Any], limit: int = 5) -> List[str]:
    insights = list(analysis.get("insights", []))
    for weakness in analysis.get("weaknesses", [])[:limit]:
        insights.append(f"可考虑加入抵抗 {weakness['type']} 的宝可梦（当前 {weakness['weak_members']} 只被克制）。")
    return insights


__all__ = [
    "ALL_TYPES",
    "global_overview",
    "player_report",
    "recommendations",
    "team_analysis",
]

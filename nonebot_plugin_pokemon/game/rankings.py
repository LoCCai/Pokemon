"""Decorate the three player boards using QWeb's cached QQ directory."""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from . import repository


def qq_number(value: Any) -> Optional[int]:
    value = str(value or "")
    if value.isascii() and value.isdecimal() and 4 <= len(value) <= 12:
        return int(value) or None
    return None


async def missing_names(players, names):
    try:
        from src.qi_web.zmws_identity import qq_name
    except ImportError:
        return
    # The host coalesces repeated lookups for a QQ and caches misses too.
    # Give one board a bounded wait even when the bot is offline.
    missing = [uid for uid in sorted(players) if not names.get(uid) or names[uid].strip() == str(uid)]
    if not missing:
        return
    slots = asyncio.Semaphore(3)

    async def fill(uid):
        async with slots:
            name = await qq_name(uid)
            if isinstance(name, str) and name.strip() not in {"", str(uid), "未知", "未知用户"}:
                names[uid] = name.strip()

    tasks = [asyncio.create_task(fill(uid)) for uid in missing]
    try:
        await asyncio.wait(tasks, timeout=2.5)
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def player_board(kind: str, viewer: str, group: Optional[str] = None, *, admin: bool = False) -> list[dict]:
    readers = {
        "score": repository.score_leaderboard,
        "pokedex": repository.pokedex_leaderboard,
        "dungeon": repository.dungeon_leaderboard,
    }
    rows = await readers.get(kind, repository.score_leaderboard)()
    players = {number for row in rows if (number := qq_number(row["uid"]))}
    names: dict[int, str] = {}
    groups: dict[int, list[str]] = {}
    if players:
        try:
            from sqlalchemy import select
            from sqlalchemy.exc import SQLAlchemyError
            from sqlalchemy.orm import aliased
            from src.qi_web.database import get_session_factory
            from src.qi_web.models import AnalyticsGroup, AnalyticsGroupMember, AnalyticsUser
        except ImportError:
            pass  # The standalone plugin has no host directory.
        else:
            member = AnalyticsGroupMember
            shared = aliased(member)
            memberships = (
                select(member.user_id, member.nickname, AnalyticsGroup.group_name)
                .join(AnalyticsGroup, AnalyticsGroup.group_id == member.group_id)
                .where(member.user_id.in_(players), member.is_active.is_(True), AnalyticsGroup.is_active.is_(True))
                .order_by(member.updated_at.desc(), member.group_id)
            )
            if not admin:
                memberships = memberships.join(shared, shared.group_id == member.group_id).where(
                    shared.user_id == qq_number(viewer), shared.is_active.is_(True)
                )
            if group is not None:
                memberships = memberships.where(member.group_id == qq_number(group))
            try:
                async with get_session_factory()() as session:
                    names.update(
                        (uid, name)
                        for uid, name in await session.execute(
                            select(AnalyticsUser.user_id, AnalyticsUser.nickname).where(
                                AnalyticsUser.user_id.in_(players)
                            )
                        )
                        if name and name.strip()
                    )
                    for uid, name, group_name in await session.execute(memberships):
                        if name:
                            names.setdefault(uid, name)
                        if group_name and group_name not in groups.setdefault(uid, []):
                            groups[uid].append(group_name)
            except SQLAlchemyError:
                from ..compat.logger import logger

                logger.warning("[pokemon] 七七群成员目录暂时不可用")
    await missing_names(players, names)
    for row in rows:
        uid = qq_number(row["uid"])
        nick = names.get(uid) if uid else None
        if not nick or nick.strip() == str(row["uid"]):
            trainer = str(row.get("nickname") or "").strip()
            nick = trainer if trainer and trainer != str(row["uid"]) else "训练家"
        row.update(nickname=nick, groups=groups.get(uid, []), avatar_url=f"/qweb/api/v1/avatars/{uid}" if uid else "")
    return rows

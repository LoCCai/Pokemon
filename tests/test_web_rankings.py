"""Visibility and identity regression for all three QWeb player boards."""

import sys
from types import ModuleType

import pytest

from nonebot_plugin_pokemon.game import rankings


@pytest.mark.asyncio
async def test_player_board_batches_real_identity_and_scopes_memberships(monkeypatch):
    pytest.importorskip("sqlalchemy")
    from sqlalchemy import BigInteger, Boolean, Column, Integer, String
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.orm import declarative_base

    base = declarative_base()

    class User(base):
        __tablename__ = "users"
        user_id = Column(BigInteger, primary_key=True)
        nickname = Column(String)

    class Group(base):
        __tablename__ = "groups"
        group_id = Column(BigInteger, primary_key=True)
        group_name = Column(String)
        is_active = Column(Boolean)

    class Member(base):
        __tablename__ = "members"
        group_id = Column(BigInteger, primary_key=True)
        user_id = Column(BigInteger, primary_key=True)
        nickname = Column(String)
        is_active = Column(Boolean, default=True)
        updated_at = Column(Integer, default=1)

    engine = create_async_engine("sqlite+aiosqlite://")
    factory = async_sessionmaker(engine)
    async with engine.begin() as conn:
        await conn.run_sync(base.metadata.create_all)
    models = ModuleType("models")
    models.AnalyticsUser, models.AnalyticsGroup, models.AnalyticsGroupMember = User, Group, Member
    db = ModuleType("database")
    db.get_session_factory = lambda: factory
    monkeypatch.setitem(sys.modules, "src.qi_web.models", models)
    monkeypatch.setitem(sys.modules, "src.qi_web.database", db)
    async with factory.begin() as session:
        session.add(User(user_id=90001, nickname="小霞"))
        for gid, name in [(1, "共同群"), (2, "另一个群"), (3, "已退群")]:
            session.add(Group(group_id=gid, group_name=name, is_active=True))
            session.add(Member(group_id=gid, user_id=90001))
        session.add(Member(group_id=1, user_id=80001))
        session.add(Member(group_id=3, user_id=80001, is_active=False))

    async def read():
        return [{"uid": "90001", "nickname": "90001"}, {"uid": "90002"}]

    try:
        for kind in ("score", "pokedex", "dungeon"):
            monkeypatch.setattr(rankings.repository, kind + "_leaderboard", read)
            first, other = await rankings.player_board(kind, "80001")
            assert (first["nickname"], first["groups"], first["avatar_url"]) == (
                "小霞",
                ["共同群"],
                "/qweb/api/v1/avatars/90001",
            )
            assert other["nickname"] == "训练家" and other["groups"] == []
            assert (await rankings.player_board(kind, "80001", "2"))[0]["groups"] == []
            assert len((await rankings.player_board(kind, "80001", admin=True))[0]["groups"]) == 3
    finally:
        await engine.dispose()

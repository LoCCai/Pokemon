"""存储后端与并发增量测试（默认 SQLite；PG 由部署联调覆盖）。"""

from __future__ import annotations

import asyncio
import os
import uuid

import pytest

from nonebot_plugin_pokemon.Pokemon.utils.dbbase.GameCounter import GAME_DB
from nonebot_plugin_pokemon.Pokemon.utils.dbbase.PokeCounter import PokeCounter
from nonebot_plugin_pokemon.Pokemon.utils.dbbase.ScoreCounter import RecordDAO, SCORE_DB
from nonebot_plugin_pokemon.Pokemon.utils.dbbase import storage


def test_translate_sql_schema_and_placeholders():
    sql = storage.translate_sql(
        "select uid from pokemon_table where uid=? limit ? offset ?",
        "postgres",
    )
    assert "qiqi_pokemon.pokemon_table" in sql
    assert sql.count("%s") == 3
    assert "?" not in sql


def test_translate_sql_upsert_to_conflict():
    sql = storage.translate_sql(
        "insert or replace into pokemon_prop (uid,prop,num) values (?,?,?)",
        "postgres",
    )
    assert "on conflict (uid, prop) do update set num = excluded.num" in sql
    assert "insert or replace" not in sql.lower()


def test_translate_sql_does_not_double_qualify_table_reference():
    sql = storage.translate_sql(
        "insert into pokemon_score (uid,score) values (?,?) "
        "on conflict (uid) do update set score=pokemon_score.score+excluded.score",
        "postgres",
    )
    assert "qiqi_pokemon.pokemon_score (uid,score)" in sql
    assert "score=pokemon_score.score+excluded.score" in sql
    assert "qiqi_pokemon.qiqi_pokemon" not in sql


def test_storage_mode_env(monkeypatch):
    monkeypatch.setenv("POKEMON_STORAGE", "postgres")
    assert storage.storage_mode() == "postgres"
    monkeypatch.setenv("POKEMON_STORAGE", "sqlite")
    assert storage.storage_mode() == "sqlite"
    monkeypatch.setenv("POKEMON_STORAGE", "not-a-backend")
    with pytest.raises(storage.StorageConfigError):
        storage.storage_mode()


def test_dsn_from_explicit_secret_and_sqlalchemy_url(monkeypatch):
    # 不打印/断言完整 DSN；只验证 scheme 规范化与 SecretStr 兼容。
    from pydantic import SecretStr

    monkeypatch.setenv("POKEMON_STORAGE", "postgres")
    monkeypatch.setenv("POKEMON_DATABASE_URL", "postgresql+psycopg://u:p@db.example:5432/poke?ssl=require")
    dsn = storage.database_dsn()
    assert dsn.startswith("postgresql://")
    assert "db.example:5432/poke" in dsn
    assert "sslmode=require" in dsn
    assert _plain(SecretStr("postgresql://u:p@db.example/poke")) == "postgresql://u:p@db.example/poke"


def _plain(value):
    from nonebot_plugin_pokemon.Pokemon.utils.dbbase.storage import _plain_secret

    return _plain_secret(value)


@pytest.fixture()
def pg_uid():
    return f"storage-{uuid.uuid4().hex[:10]}"


async def test_score_limiter_and_inventory_are_atomic(pg_uid):
    uid = pg_uid
    score = SCORE_DB()
    poke = PokeCounter()
    game = GAME_DB()
    await score.update_score(uid, 0)
    await score.update_shengwang(uid, 0)

    await asyncio.gather(*[score.update_score(uid, 1) for _ in range(30)])
    await asyncio.gather(*[score.update_shengwang(uid, 2) for _ in range(15)])
    assert await score.get_score(uid) == 30
    assert await score.get_shengwang(uid) == 30

    await asyncio.gather(*[poke._add_pokemon_prop(uid, "神奇糖果", 1) for _ in range(25)])
    assert await poke._get_pokemon_prop(uid, "神奇糖果") == 25
    await asyncio.gather(*[poke._add_pokemon_egg(uid, 25, 1) for _ in range(20)])
    assert await poke.get_pokemon_egg(uid, 25) == 20

    await asyncio.gather(*[game.update_game_num(uid, "whotj") for _ in range(12)])
    assert await game.get_game_num(uid, "whotj") == 12
    await asyncio.gather(*[poke.update_chongsheng(uid, 384, 1) for _ in range(12)])
    assert await poke.get_chongsheng_num(uid, 384) == 12

    dao = RecordDAO()
    key = (uid, "work")
    assert dao.get_num(key) == 0
    dao.increment_key(key, 4)
    assert dao.get_num(key) == 4
    dao.set_date(20260101, key)
    assert dao.get_date(key) == 20260101
    dao.clear_key(key)
    assert dao.get_num(key) == 0


async def test_async_storage_does_not_modify_sqlite_schema(pg_uid):
    # SQLite 模式仍走原有兼容路径；PG 模式 verify_schema 只读，已由联调脚本覆盖。
    if os.getenv("POKEMON_STORAGE", "sqlite").lower() in {"postgres", "postgresql", "pg"}:
        pytest.skip("当前进程为 PG 模式")
    await storage.verify_schema()
    await storage.execute("select 1")


def test_nonebot_config_fallback_without_env(monkeypatch):
    from pydantic import SecretStr

    from nonebot_plugin_pokemon.config import plugin_config

    monkeypatch.delenv("POKEMON_STORAGE", raising=False)
    monkeypatch.delenv("POKEMON_DATABASE_URL", raising=False)
    monkeypatch.setattr(plugin_config, "pokemon_storage", "postgres", raising=False)
    monkeypatch.setattr(
        plugin_config,
        "pokemon_database_url",
        SecretStr("postgresql://u:p@db.example:5432/poke"),
        raising=False,
    )
    assert storage.storage_mode() == "postgres"
    assert storage.database_dsn().startswith("postgresql://")


def test_host_settings_database_url_fallback(monkeypatch):
    import sys
    from types import ModuleType, SimpleNamespace

    from pydantic import SecretStr

    monkeypatch.delenv("POKEMON_DATABASE_URL", raising=False)
    monkeypatch.setenv("POKEMON_STORAGE", "postgres")

    config_module = ModuleType("src.qi_web.config")
    settings = SimpleNamespace(
        database_url=SecretStr("postgresql+asyncpg://u:p@db.example:5432/poke?ssl=require"),
        database_ssl_mode="auto",
    )
    config_module.get_settings = lambda: settings  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "src.qi_web.config", config_module)

    dsn = storage.database_dsn()
    assert dsn.startswith("postgresql://")
    assert "sslmode=require" in dsn


def test_storage_error_does_not_echo_dsn(monkeypatch):
    monkeypatch.delenv("POKEMON_DATABASE_URL", raising=False)
    monkeypatch.setenv("POKEMON_STORAGE", "postgres")
    monkeypatch.setitem(__import__("sys").modules, "src.qi_web.config", None)

    with pytest.raises(storage.StorageConfigError) as excinfo:
        storage.database_dsn()
    assert "postgresql://" not in str(excinfo.value)

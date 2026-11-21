"""数据库后端选择：SQLite（默认）与 PostgreSQL（七七生产）。

设计约束
========

* SQLite 仍是默认后端，现有单机数据与调用方式不变；
* 只有显式 ``POKEMON_STORAGE=postgres`` 才启用 PostgreSQL；
* PostgreSQL 使用独立 schema ``qiqi_pokemon``，表名/列名均为小写且不加引号；
* 运行时绝不创建、修改 schema 或表结构，只做只读预检和 DML；
* 所有 SQL 都是静态语句，外部值只通过参数绑定进入数据库；
* DSN 只在建立连接时读取，不进入日志、异常文本或公开接口。

生产 DSN 优先取显式的 ``POKEMON_DATABASE_URL``（环境变量或 NoneBot 配置），
否则复用 ``src.qi_web.config.get_settings().database_url``。后者可能是
``SecretStr``、``str`` 或 SQLAlchemy 风格 URL，这里统一转换成 psycopg DSN。
"""

from __future__ import annotations

import asyncio
import os
import re
import threading
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from ..resource.RESOURCE_PATH import MAIN_PATH

SCHEMA = "qiqi_pokemon"
SQLITE_DB_PATH = os.path.expanduser(MAIN_PATH / "pokemon.db")

# 逻辑表名 -> 小写物理表名。PG schema 导入由部署方负责，运行时只使用这些表。
TABLES: Dict[str, str] = {
    "pokemon_table": "pokemon_table",
    "pokemon_map": "pokemon_map",
    "pokemon_team": "pokemon_team",
    "pokemon_egg": "pokemon_egg",
    "pokemon_prop": "pokemon_prop",
    "pokemon_star": "pokemon_star",
    "pokemon_starrush": "pokemon_starrush",
    "map_refresh": "map_refresh",
    "refresh_send": "refresh_send",
    "prop_exchange": "prop_exchange",
    "prop_technical": "prop_technical",
    "boss_fight": "boss_fight",
    "chongsheng": "chongsheng",
    "poke_pipei": "poke_pipei",
    "poke_dungeon": "poke_dungeon",
    "pokemon_score": "pokemon_score",
    "pokemon_game": "pokemon_game",
    "limiter": "limiter",
}

# 对应 SQLite 的 PRIMARY KEY，用于把 INSERT OR REPLACE 转成 ON CONFLICT。
CONFLICT_TARGETS: Dict[str, Tuple[str, ...]] = {
    "pokemon_table": ("uid", "bianhao"),
    "pokemon_map": ("uid",),
    "pokemon_team": ("uid",),
    "pokemon_egg": ("uid", "bianhao"),
    "pokemon_prop": ("uid", "prop"),
    "pokemon_star": ("uid", "bianhao"),
    "pokemon_starrush": ("uid",),
    "map_refresh": ("diqu",),
    "refresh_send": ("groupid",),
    "prop_exchange": ("exchangeid",),
    "prop_technical": ("uid", "prop"),
    "boss_fight": ("uid", "time"),
    "chongsheng": ("uid", "bianhao"),
    "poke_pipei": ("uid",),
    "poke_dungeon": ("uid",),
    "pokemon_score": ("uid",),
    "pokemon_game": ("uid", "type"),
    "limiter": ("key",),
}

# 只用于启动预检；不生成 DDL。
EXPECTED_COLUMNS: Dict[str, Tuple[str, ...]] = {
    "pokemon_table": (
        "uid",
        "bianhao",
        "level",
        "exp",
        "gt_hp",
        "gt_atk",
        "gt_def",
        "gt_stk",
        "gt_sef",
        "gt_spd",
        "nl_hp",
        "nl_atk",
        "nl_def",
        "nl_stk",
        "nl_sef",
        "nl_spd",
        "xingge",
        "jineng",
        "xiedai",
    ),
    "pokemon_map": ("uid", "huizhang", "map_name", "nickname", "pipei", "autoflag", "autotime"),
    "pokemon_team": ("uid", "team"),
    "pokemon_egg": ("uid", "bianhao", "num"),
    "pokemon_prop": ("uid", "prop", "num"),
    "pokemon_star": ("uid", "bianhao", "type"),
    "pokemon_starrush": ("uid", "num"),
    "map_refresh": ("diqu", "didian", "pokemon"),
    "refresh_send": ("groupid", "botid"),
    "prop_exchange": ("exchangeid", "proptype", "propname", "num", "uid", "score", "uptime"),
    "prop_technical": ("uid", "prop", "num"),
    "boss_fight": ("uid", "shanghai", "time"),
    "chongsheng": ("uid", "bianhao", "num"),
    "poke_pipei": ("uid", "flag", "fightid", "diuid", "fighttype"),
    "poke_dungeon": ("uid", "num"),
    "pokemon_score": ("uid", "score", "shengwang"),
    "pokemon_game": ("uid", "type", "num"),
    "limiter": ("key", "num", "date"),
}


class StorageError(RuntimeError):
    """存储层错误。文本中不包含 DSN。"""


class StorageConfigError(StorageError):
    """存储配置错误。文本中不包含 DSN。"""


def _config_value(name: str) -> str:
    """读取环境变量或 NoneBot 同名配置。

    ``.env.prod`` 不一定进入 ``os.environ``，所以 NoneBot 的 ``Config``
    是必须的兜底。显式环境变量优先。
    """

    raw_env = os.getenv(name, "")
    if raw_env is not None and str(raw_env).strip():
        return str(raw_env).strip()
    try:
        from ....config import plugin_config  # 延迟导入，避免插件导入环

        raw = getattr(plugin_config, name.lower(), "")
        if hasattr(raw, "get_secret_value"):
            raw = raw.get_secret_value()
        if raw is not None and str(raw).strip():
            return str(raw).strip()
    except Exception:
        pass
    return ""


def storage_mode() -> str:
    """返回 ``sqlite`` 或 ``postgres``。未知值直接报配置错误。"""

    raw = _config_value("POKEMON_STORAGE").lower()
    if raw in {"", "sqlite", "sqlite3"}:
        return "sqlite"
    if raw in {"postgres", "postgresql", "pg"}:
        return "postgres"
    raise StorageConfigError("POKEMON_STORAGE 只能是 sqlite 或 postgres")


def is_postgres() -> bool:
    return storage_mode() == "postgres"


def _plain_secret(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "get_secret_value"):
        value = value.get_secret_value()
    return str(value).strip()


def _explicit_database_url() -> str:
    """显式配置：环境变量优先，其次 NoneBot 配置。"""

    raw = os.getenv("POKEMON_DATABASE_URL", "")
    if raw is not None and str(raw).strip():
        return _plain_secret(raw)
    try:
        from ....config import plugin_config

        return _plain_secret(getattr(plugin_config, "pokemon_database_url", ""))
    except Exception:
        return ""


def _host_database_url() -> str:
    """复用宿主 ``src.qi_web.config.get_settings().database_url``。"""

    try:
        from src.qi_web.config import get_settings  # type: ignore

        settings = get_settings()
        return _libpq_url(_plain_secret(settings.database_url), getattr(settings, "database_ssl_mode", "auto"))
    except Exception:
        return ""


def _libpq_url(value: str, ssl_mode: str = "auto") -> str:
    """Translate a QWeb SQLAlchemy URI while preserving its encoded credentials."""
    from urllib.parse import parse_qsl, urlencode, urlsplit

    if "://" not in value:
        return value
    parts = urlsplit(value)
    if parts.scheme.split("+", 1)[0] not in {"postgres", "postgresql"}:
        raise ValueError("Unsupported PostgreSQL URL scheme")
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    if "ssl" in query:
        query.setdefault("sslmode", query.pop("ssl"))
    if ssl_mode and ssl_mode != "auto":
        query.setdefault("sslmode", ssl_mode)
    suffix = "?" + urlencode(query) if query else ""
    return f"postgresql://{parts.netloc}{parts.path}{suffix}"


def database_dsn() -> str:
    """解析 PostgreSQL DSN，绝不输出内容。"""

    try:
        dsn = _libpq_url(_explicit_database_url()) or _host_database_url()
    except ValueError:
        raise StorageConfigError("POKEMON_DATABASE_URL 不是受支持的 PostgreSQL URL") from None
    if not dsn:
        raise StorageConfigError(
            "已启用 PostgreSQL，但未配置 POKEMON_DATABASE_URL，"
            "也无法从 src.qi_web.config.get_settings().database_url 读取数据库地址"
        )
    return dsn


# --------------------------------------------------------------------------- SQL


_UPSERT_RE = re.compile(
    r"\binsert\s+or\s+replace\s+into\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]+)\)\s*values\s*\(([^)]+)\)",
    re.IGNORECASE | re.DOTALL,
)


def _table_regex() -> re.Pattern[str]:
    names = sorted(TABLES, key=len, reverse=True)
    return re.compile(
        r"\b(" + "|".join(re.escape(name) for name in names) + r")\b(?!\s*\.)",
        re.IGNORECASE,
    )


_TABLE_RE = _table_regex()


def _translate_upsert(sql: str) -> str:
    """把 SQLite ``INSERT OR REPLACE`` 转为 PostgreSQL ``ON CONFLICT``。"""

    match = _UPSERT_RE.search(sql)
    if not match:
        return sql
    table = match.group(1).lower()
    target = CONFLICT_TARGETS.get(table)
    if not target:
        return sql
    columns = [part.strip().lower() for part in match.group(2).split(",") if part.strip()]
    updates = [column for column in columns if column not in target]
    if updates:
        assignment = ", ".join(f"{column} = excluded.{column}" for column in updates)
        replacement = (
            f"insert into {table} ({', '.join(columns)}) values ({match.group(3)}) "
            f"on conflict ({', '.join(target)}) do update set {assignment}"
        )
    else:
        replacement = (
            f"insert into {table} ({', '.join(columns)}) values ({match.group(3)}) "
            f"on conflict ({', '.join(target)}) do nothing"
        )
    return sql[: match.start()] + replacement + sql[match.end() :]


def translate_sql(sql: str, backend: Optional[str] = None) -> str:
    """把静态 SQL 翻译为目标后端方言。

    仅处理静态结构（schema、占位符、SQLite upsert）；外部值永远是参数。
    """

    backend = backend or storage_mode()
    if backend != "postgres":
        return sql
    translated = _translate_upsert(sql)
    translated = _TABLE_RE.sub(lambda m: f"{SCHEMA}.{m.group(1).lower()}", translated)
    translated = translated.replace("?", "%s")
    # SQLite 的 INSERT OR IGNORE 不在本项目中动态拼接；如需兼容可在此扩展。
    return translated


def _params(values: Optional[Iterable[Any]]) -> Tuple[Any, ...]:
    if values is None:
        return ()
    # bool 在 PG 中是 boolean，显式转成 int 以匹配旧 SQLite 的 0/1 整数列。
    return tuple(int(value) if isinstance(value, bool) else value for value in values)


def _pg_error_message(exc: Exception) -> str:
    """构造安全错误文本：只含异常类型/服务端 SQLSTATE/主消息，不含 DSN。"""

    diag = getattr(exc, "diag", None)
    primary = getattr(diag, "message_primary", None) if diag is not None else None
    state = getattr(diag, "sqlstate", None) if diag is not None else None
    message = f"PostgreSQL 操作失败（{type(exc).__name__}"
    if state:
        message += f", sqlstate={state}"
    message += "）"
    if primary:
        message += f": {primary}"
    return message


# --------------------------------------------------------------------------- async


class _SQLiteAsync:
    async def fetchall(self, sql: str, params: Optional[Iterable[Any]] = None) -> List[Sequence[Any]]:
        import aiosqlite

        async with aiosqlite.connect(SQLITE_DB_PATH) as connection:
            cursor = await connection.execute(sql, _params(params))
            try:
                return list(await cursor.fetchall())
            finally:
                await cursor.close()

    async def fetchone(self, sql: str, params: Optional[Iterable[Any]] = None) -> Optional[Sequence[Any]]:
        import aiosqlite

        async with aiosqlite.connect(SQLITE_DB_PATH) as connection:
            cursor = await connection.execute(sql, _params(params))
            try:
                return await cursor.fetchone()
            finally:
                await cursor.close()

    async def execute(self, sql: str, params: Optional[Iterable[Any]] = None) -> None:
        import aiosqlite

        async with aiosqlite.connect(SQLITE_DB_PATH) as connection:
            try:
                await connection.execute(sql, _params(params))
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise

    async def execute_returning(
        self, sql: str, params: Optional[Iterable[Any]] = None
    ) -> Optional[Sequence[Any]]:
        import aiosqlite

        async with aiosqlite.connect(SQLITE_DB_PATH) as connection:
            try:
                cursor = await connection.execute(sql, _params(params))
                row = await cursor.fetchone()
                await connection.commit()
                return row
            except Exception:
                await connection.rollback()
                raise


class _PostgresAsync:
    def __init__(self) -> None:
        self._pools: Dict[int, Tuple[Any, Any]] = {}
        self._locks: Dict[int, asyncio.Lock] = {}

    async def _pool(self) -> Any:
        loop = asyncio.get_running_loop()
        key = id(loop)
        lock = self._locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[key] = lock
        async with lock:
            current = self._pools.get(key)
            if current is not None and current[0] is loop:
                return current[1]

            try:
                from psycopg_pool import AsyncConnectionPool
            except ImportError:
                raise StorageError("PostgreSQL 后端需要 psycopg[binary,pool]>=3.2,<4") from None

            pool = AsyncConnectionPool(
                conninfo=database_dsn(),
                min_size=1,
                max_size=8,
                open=False,
                kwargs={"autocommit": False},
            )
            try:
                await pool.open(wait=True)
            except Exception as exc:
                try:
                    await pool.close()
                except Exception:
                    pass
                raise StorageError(_pg_error_message(exc)) from None
            self._pools[key] = (loop, pool)
            return pool

    @asynccontextmanager
    async def connection(self):
        active = _active_pg_connection.get()
        if active is not None:
            yield active
            return
        pool = await self._pool()
        async with pool.connection() as connection:
            yield connection

    async def _fetch(self, sql, params, *, one):
        try:
            async with self.connection() as connection, connection.cursor() as cursor:
                await cursor.execute(translate_sql(sql, "postgres"), _params(params))
                return await cursor.fetchone() if one else await cursor.fetchall()
        except StorageError:
            raise
        except Exception as exc:
            raise StorageError(_pg_error_message(exc)) from None

    async def fetchall(self, sql: str, params: Optional[Iterable[Any]] = None) -> List[Sequence[Any]]:
        return list(await self._fetch(sql, params, one=False))

    async def fetchone(self, sql: str, params: Optional[Iterable[Any]] = None) -> Optional[Sequence[Any]]:
        return await self._fetch(sql, params, one=True)

    async def _execute(self, sql, params, *, returning):
        try:
            async with self.connection() as connection, connection.cursor() as cursor:
                await cursor.execute(translate_sql(sql, "postgres"), _params(params))
                return await cursor.fetchone() if returning else None
        except StorageError:
            raise
        except Exception as exc:
            raise StorageError(_pg_error_message(exc)) from None

    async def execute(self, sql: str, params: Optional[Iterable[Any]] = None) -> None:
        await self._execute(sql, params, returning=False)

    async def execute_returning(
        self, sql: str, params: Optional[Iterable[Any]] = None
    ) -> Optional[Sequence[Any]]:
        return await self._execute(sql, params, returning=True)

    async def close(self) -> None:
        for _, pool in list(self._pools.values()):
            try:
                await pool.close()
            except Exception:
                pass
        self._pools.clear()
        self._locks.clear()


class _SQLiteSync:
    def _connect(self) -> Any:
        import sqlite3

        return sqlite3.connect(SQLITE_DB_PATH)

    def fetchall(self, sql: str, params: Optional[Iterable[Any]] = None) -> List[Sequence[Any]]:
        with self._connect() as connection:
            cursor = connection.execute(sql, _params(params))
            try:
                return list(cursor.fetchall())
            finally:
                cursor.close()

    def fetchone(self, sql: str, params: Optional[Iterable[Any]] = None) -> Optional[Sequence[Any]]:
        with self._connect() as connection:
            cursor = connection.execute(sql, _params(params))
            try:
                return cursor.fetchone()
            finally:
                cursor.close()

    def execute(self, sql: str, params: Optional[Iterable[Any]] = None) -> None:
        with self._connect() as connection:
            connection.execute(sql, _params(params))
            connection.commit()

    def execute_returning(
        self, sql: str, params: Optional[Iterable[Any]] = None
    ) -> Optional[Sequence[Any]]:
        with self._connect() as connection:
            cursor = connection.execute(sql, _params(params))
            row = cursor.fetchone()
            connection.commit()
            return row


class _PostgresSync:
    def __init__(self) -> None:
        self._pool_obj: Any = None
        self._lock = threading.Lock()

    def _pool(self) -> Any:
        with self._lock:
            if self._pool_obj is not None:
                return self._pool_obj
            try:
                from psycopg_pool import ConnectionPool
            except ImportError:
                raise StorageError("PostgreSQL 后端需要 psycopg[binary,pool]>=3.2,<4") from None

            pool = ConnectionPool(
                conninfo=database_dsn(),
                min_size=1,
                max_size=4,
                open=False,
                kwargs={"autocommit": False},
            )
            try:
                pool.open(wait=True)
            except Exception as exc:
                try:
                    pool.close()
                except Exception:
                    pass
                raise StorageError(_pg_error_message(exc)) from None
            self._pool_obj = pool
            return pool

    def _fetch(self, sql: str, params: Optional[Iterable[Any]], *, one: bool) -> Any:
        translated = translate_sql(sql, "postgres")
        try:
            pool = self._pool()
            with pool.connection() as connection:
                try:
                    cursor = connection.execute(translated, _params(params))
                    row = cursor.fetchone() if one else cursor.fetchall()
                    connection.commit()
                    return row
                except Exception:
                    try:
                        connection.rollback()
                    except Exception:
                        pass
                    raise
        except StorageError:
            raise
        except Exception as exc:
            raise StorageError(_pg_error_message(exc)) from None

    def fetchall(self, sql: str, params: Optional[Iterable[Any]] = None) -> List[Sequence[Any]]:
        return list(self._fetch(sql, params, one=False))

    def fetchone(self, sql: str, params: Optional[Iterable[Any]] = None) -> Optional[Sequence[Any]]:
        return self._fetch(sql, params, one=True)

    def _execute(self, sql: str, params: Optional[Iterable[Any]], *, returning: bool) -> Any:
        translated = translate_sql(sql, "postgres")
        try:
            pool = self._pool()
            with pool.connection() as connection:
                try:
                    cursor = connection.execute(translated, _params(params))
                    row = cursor.fetchone() if returning else None
                    connection.commit()
                    return row
                except Exception:
                    try:
                        connection.rollback()
                    except Exception:
                        pass
                    raise
        except StorageError:
            raise
        except Exception as exc:
            raise StorageError(_pg_error_message(exc)) from None

    def execute(self, sql: str, params: Optional[Iterable[Any]] = None) -> None:
        self._execute(sql, params, returning=False)

    def execute_returning(
        self, sql: str, params: Optional[Iterable[Any]] = None
    ) -> Optional[Sequence[Any]]:
        return self._execute(sql, params, returning=True)

    def close(self) -> None:
        with self._lock:
            pool = self._pool_obj
            self._pool_obj = None
        if pool is not None:
            try:
                pool.close()
            except Exception:
                pass


_sqlite_async = _SQLiteAsync()
_postgres_async = _PostgresAsync()
_sqlite_sync = _SQLiteSync()
_postgres_sync = _PostgresSync()


_active_pg_connection: ContextVar[Any] = ContextVar("pokemon_transaction", default=None)


@asynccontextmanager
async def starter_transaction(uid: str):
    """Serialize first claims from QQ and QWeb, including the empty-inventory case."""
    if not is_postgres():
        yield
        return
    async with _postgres_async.connection() as connection, connection.transaction():
        await connection.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                                 ("qiqi_pokemon.starter:" + str(uid),))
        token = _active_pg_connection.set(connection)
        try:
            yield
        finally:
            _active_pg_connection.reset(token)


def async_database() -> Any:
    return _postgres_async if is_postgres() else _sqlite_async


def sync_database() -> Any:
    return _postgres_sync if is_postgres() else _sqlite_sync


async def fetchall(sql: str, params: Optional[Iterable[Any]] = None) -> List[Sequence[Any]]:
    return await async_database().fetchall(sql, params)


async def fetchone(sql: str, params: Optional[Iterable[Any]] = None) -> Optional[Sequence[Any]]:
    return await async_database().fetchone(sql, params)


async def execute(sql: str, params: Optional[Iterable[Any]] = None) -> None:
    await async_database().execute(sql, params)


async def execute_returning(
    sql: str, params: Optional[Iterable[Any]] = None
) -> Optional[Sequence[Any]]:
    return await async_database().execute_returning(sql, params)


def fetchall_sync(sql: str, params: Optional[Iterable[Any]] = None) -> List[Sequence[Any]]:
    return sync_database().fetchall(sql, params)


def fetchone_sync(sql: str, params: Optional[Iterable[Any]] = None) -> Optional[Sequence[Any]]:
    return sync_database().fetchone(sql, params)


def execute_sync(sql: str, params: Optional[Iterable[Any]] = None) -> None:
    sync_database().execute(sql, params)


def execute_returning_sync(
    sql: str, params: Optional[Iterable[Any]] = None
) -> Optional[Sequence[Any]]:
    return sync_database().execute_returning(sql, params)


async def verify_schema() -> None:
    """只读检查 PG schema 是否包含运行时需要的表和列，不创建/修改任何对象。"""

    if not is_postgres():
        return
    rows = await _postgres_async.fetchall(
        "select table_name, column_name from information_schema.columns where table_schema = ?",
        (SCHEMA,),
    )
    found: Dict[str, set[str]] = {}
    for table, column in rows:
        found.setdefault(str(table).lower(), set()).add(str(column).lower())

    missing_tables = [table for table in TABLES if table not in found]
    if missing_tables:
        names = ", ".join(f"{SCHEMA}.{table}" for table in missing_tables)
        raise StorageError(f"PostgreSQL schema 缺少表：{names}")

    missing_columns: List[str] = []
    for table, columns in EXPECTED_COLUMNS.items():
        actual = found.get(table, set())
        for column in columns:
            if column not in actual:
                missing_columns.append(f"{SCHEMA}.{table}.{column}")
    if missing_columns:
        raise StorageError("PostgreSQL schema 缺少列：" + ", ".join(missing_columns))


async def close_storage() -> None:
    await _postgres_async.close()
    await asyncio.to_thread(_postgres_sync.close)


__all__ = [
    "CONFLICT_TARGETS",
    "EXPECTED_COLUMNS",
    "SCHEMA",
    "SQLITE_DB_PATH",
    "StorageConfigError",
    "StorageError",
    "TABLES",
    "async_database",
    "close_storage",
    "database_dsn",
    "execute",
    "execute_returning",
    "execute_returning_sync",
    "execute_sync",
    "fetchall",
    "fetchall_sync",
    "fetchone",
    "fetchone_sync",
    "is_postgres",
    "storage_mode",
    "sync_database",
    "translate_sql",
    "verify_schema",
]

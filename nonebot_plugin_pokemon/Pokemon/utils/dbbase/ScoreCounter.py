import json
import os
import sqlite3

from .storage import (
    SQLITE_DB_PATH,
    execute,
    execute_sync,
    fetchone,
    fetchone_sync,
    is_postgres,
)

DB_PATH = SQLITE_DB_PATH


class SCORE_DB:
    def __init__(self):
        # PG schema 由部署方导入；运行时只做 DML。
        if not is_postgres():
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            self._create_table()

    def _connect(self):
        return sqlite3.connect(DB_PATH)

    def _create_table(self):
        try:
            with self._connect() as connection:
                connection.execute(
                    """CREATE TABLE IF NOT EXISTS POKEMON_SCORE
                              (UID             TEXT   NOT NULL,
                               SCORE           INT    NOT NULL,
                               SHENGWANG       INT    NOT NULL,
                               PRIMARY KEY(UID));"""
                )
        except Exception:
            raise Exception('创建表发生错误')

    async def _new_score(self, uid):
        # 只保证行存在，不能把并发创建者已有的积分重置为 0。
        await execute(
            "insert into pokemon_score (uid,score,shengwang) values (?,?,?) "
            "on conflict (uid) do nothing",
            (str(uid), 0, 0),
        )

    async def delete_score(self, uid):
        await execute("delete from pokemon_score where uid=?", (str(uid),))

    async def change_score(self, newuid, olduid):
        await execute(
            "update pokemon_score set uid=? where uid=?",
            (str(newuid), str(olduid)),
        )

    async def get_score(self, uid):
        row = await fetchone(
            "select score from pokemon_score where uid=?",
            (str(uid),),
        )
        if row:
            return int(row[0])
        await self._new_score(uid)
        return 0

    async def update_score(self, uid, score):
        # 原子增量：不再 SELECT 后 SET，避免并发丢失更新。
        await execute(
            "insert into pokemon_score (uid,score,shengwang) values (?,?,?) "
            "on conflict (uid) do update set score=pokemon_score.score+excluded.score",
            (str(uid), int(score), 0),
        )

    async def get_shengwang(self, uid):
        row = await fetchone(
            "select shengwang from pokemon_score where uid=?",
            (str(uid),),
        )
        if row:
            return int(row[0])
        await self._new_score(uid)
        return 0

    async def update_shengwang(self, uid, shengwang):
        await execute(
            "insert into pokemon_score (uid,score,shengwang) values (?,?,?) "
            "on conflict (uid) do update set shengwang=pokemon_score.shengwang+excluded.shengwang",
            (str(uid), 0, int(shengwang)),
        )


class RecordDAO:
    """同步限次记录。

    SQLite 仍使用原来的同步 sqlite3；PG 使用独立同步连接池（psycopg_pool），
    以便现有 ``DailyAmountLimiter.check()/increase()`` 这类同步调用继续工作。
    """

    def __init__(self):
        self.db_path = DB_PATH
        if not is_postgres():
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            self._create_table()

    def connect(self):
        return sqlite3.connect(self.db_path)

    def _create_table(self):
        if is_postgres():
            return
        with self.connect() as conn:
            conn.execute(
                'CREATE TABLE IF NOT EXISTS limiter'
                '(key TEXT NOT NULL, num INT NOT NULL, date INT, PRIMARY KEY(key))'
            )

    @staticmethod
    def _key(key):
        # 旧实现把 tuple 直接绑给 sqlite3（实际无法绑定）。这里统一成稳定文本，
        # 既让 SQLite 限次真正生效，也让 PG 的 TEXT 主键可用。
        if isinstance(key, (tuple, list)):
            return json.dumps([str(item) for item in key], ensure_ascii=False, separators=(",", ":"))
        return str(key)

    def exist_check(self, key):
        execute_sync(
            "insert into limiter (key,num,date) values (?,?,?) "
            "on conflict (key) do nothing",
            (self._key(key), 0, -1),
        )

    def get_num(self, key):
        record_key = self._key(key)
        self.exist_check(record_key)
        row = fetchone_sync(
            "select num from limiter where key=?",
            (record_key,),
        )
        return int(row[0]) if row else 0

    def clear_key(self, key):
        record_key = self._key(key)
        self.exist_check(record_key)
        execute_sync(
            "update limiter set num=? where key=?",
            (0, record_key),
        )

    def increment_key(self, key, num):
        record_key = self._key(key)
        self.exist_check(record_key)
        execute_sync(
            "update limiter set num=num+? where key=?",
            (int(num), record_key),
        )

    def get_date(self, key):
        record_key = self._key(key)
        self.exist_check(record_key)
        row = fetchone_sync(
            "select date from limiter where key=?",
            (record_key,),
        )
        return int(row[0]) if row else 0

    def set_date(self, date, key):
        record_key = self._key(key)
        self.exist_check(record_key)
        execute_sync(
            "update limiter set date=? where key=?",
            (int(date), record_key),
        )


__all__ = ["DB_PATH", "RecordDAO", "SCORE_DB"]

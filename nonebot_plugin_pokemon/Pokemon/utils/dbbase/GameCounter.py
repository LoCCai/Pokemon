import os
import sqlite3

from .storage import SQLITE_DB_PATH, execute_returning, is_postgres

DB_PATH = SQLITE_DB_PATH


class GAME_DB:
    def __init__(self):
        if not is_postgres():
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            self._create_table()

    def _connect(self):
        return sqlite3.connect(DB_PATH)

    def _create_table(self):
        try:
            with self._connect() as connection:
                connection.execute(
                    """CREATE TABLE IF NOT EXISTS POKEMON_GAME
                              (UID             TEXT   NOT NULL,
                               TYPE            TEXT   NOT NULL,
                               NUM             INT    NOT NULL,
                               PRIMARY KEY(UID, TYPE));"""
                )
        except Exception:
            raise Exception('创建表发生错误')

    async def _new_game_num(self, uid, gametype):
        # 按旧语义仅在缺失时建行；并发创建不会把已有计数重置。
        from .storage import execute

        await execute(
            "insert into pokemon_game (uid,type,num) values (?,?,?) "
            "on conflict (uid,type) do nothing",
            (str(uid), str(gametype), 0),
        )

    async def get_game_num(self, uid, gametype):
        from .storage import fetchone

        row = await fetchone(
            "select num from pokemon_game where uid=? and type=?",
            (str(uid), str(gametype)),
        )
        if row:
            return int(row[0])
        await self._new_game_num(uid, gametype)
        return 0

    async def update_game_num(self, uid, gametype, num=1):
        # 单条原子 upsert + RETURNING，避免并发读改写丢计数。
        row = await execute_returning(
            "insert into pokemon_game (uid,type,num) values (?,?,?) "
            "on conflict (uid,type) do update set num=pokemon_game.num+excluded.num returning num",
            (str(uid), str(gametype), int(num)),
        )
        return int(row[0]) if row else 0


__all__ = ["DB_PATH", "GAME_DB"]

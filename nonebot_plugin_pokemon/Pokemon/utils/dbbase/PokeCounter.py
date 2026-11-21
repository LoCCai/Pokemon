import os
import sqlite3

from .storage import (
    SQLITE_DB_PATH,
    execute,
    execute_returning,
    fetchall,
    fetchone,
    is_postgres,
)

DB_PATH = SQLITE_DB_PATH


def _int(value):
    if value is None:
        return 0
    if isinstance(value, bool):
        return int(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(float(value))


def _text(value):
    return "" if value is None else str(value)


def _clamp_zero(expression):
    # SQLite 用 max()，PostgreSQL 用 greatest()；expression 必须是静态片段。
    return f"greatest(0, {expression})" if is_postgres() else f"max(0, {expression})"


class PokeCounter:
    def __init__(self):
        # PostgreSQL 的表结构、索引与数据迁移由部署方负责。运行时只使用表，
        # 绝不在 PG 中执行 CREATE/ALTER；启动预检见 storage.verify_schema()。
        if is_postgres():
            return
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self._create_table()
        self._create_table_map()
        self._create_table_group()
        self._create_table_egg()
        self._create_table_prop()
        self._create_table_star()
        self._create_table_starrush()
        self._create_table_map_refresh()
        self._create_table_refresh_send()
        self._create_table_exchange()
        self._create_table_technical()
        self._create_table_boss_fight()
        self._create_table_chongsheng_num()
        self._create_table_pipei_table()
        self._truncate_table_pipei()
        self._create_map_pipei_add()
        self._create_table_dungeon()
        self._create_mapauto_add()
        self._create_poketable_add()

    def _connect(self):
        return sqlite3.connect(DB_PATH)

    def _create_table(self):
        try:
            self._connect().execute(
                """CREATE TABLE IF NOT EXISTS POKEMON_TABLE
                          (UID             TEXT   NOT NULL,
                           BIANHAO         INT    NOT NULL,
                           LEVEL           INT    NOT NULL,
                           EXP             INT    NOT NULL,
                           GT_HP           INT    NOT NULL,
                           GT_ATK          INT    NOT NULL,
                           GT_DEF          INT    NOT NULL,
                           GT_STK          INT    NOT NULL,
                           GT_SEF          INT    NOT NULL,
                           GT_SPD          INT    NOT NULL,
                           NL_HP           INT    NOT NULL,
                           NL_ATK          INT    NOT NULL,
                           NL_DEF          INT    NOT NULL,
                           NL_STK          INT    NOT NULL,
                           NL_SEF          INT    NOT NULL,
                           NL_SPD          INT    NOT NULL,
                           XINGGE          TEXT   NOT NULL,
                           JINENG          TEXT   NOT NULL,
                           PRIMARY KEY(UID,BIANHAO));"""
            )
        except:
            raise Exception('创建表发生错误')

    def _create_table_map(self):
        try:
            self._connect().execute(
                """CREATE TABLE IF NOT EXISTS POKEMON_MAP
                          (UID             TEXT   NOT NULL,
                           HUIZHANG        TEXT   NOT NULL,
                           MAP_NAME        TEXT   NOT NULL,
                           NICKNAME        TEXT   NOT NULL,
                           PRIMARY KEY(UID));"""
            )
        except:
            raise Exception('创建表发生错误')

    def _create_table_group(self):
        try:
            self._connect().execute(
                """CREATE TABLE IF NOT EXISTS POKEMON_TEAM
                          (UID             TEXT   NOT NULL,
                           TEAM            TEXT   NOT NULL,
                           PRIMARY KEY(UID));"""
            )
        except:
            raise Exception('创建表发生错误')

    def _create_table_egg(self):
        try:
            self._connect().execute(
                """CREATE TABLE IF NOT EXISTS POKEMON_EGG
                          (UID             TEXT   NOT NULL,
                           BIANHAO         INT    NOT NULL,
                           NUM             INT    NOT NULL,
                           PRIMARY KEY(UID, BIANHAO));"""
            )
        except:
            raise Exception('创建表发生错误')

    def _create_table_prop(self):
        try:
            self._connect().execute(
                """CREATE TABLE IF NOT EXISTS POKEMON_PROP
                          (UID             TEXT   NOT NULL,
                           PROP            TEXT   NOT NULL,
                           NUM             INT    NOT NULL,
                           PRIMARY KEY(UID, PROP));"""
            )
        except:
            raise Exception('创建表发生错误')

    def _create_table_star(self):
        try:
            self._connect().execute(
                """CREATE TABLE IF NOT EXISTS POKEMON_STAR
                          (UID             TEXT   NOT NULL,
                           BIANHAO         INT    NOT NULL,
                           TYPE            INT    NOT NULL,
                           PRIMARY KEY(UID, BIANHAO));"""
            )
        except:
            raise Exception('创建表发生错误')

    def _create_table_starrush(self):
        try:
            self._connect().execute(
                """CREATE TABLE IF NOT EXISTS POKEMON_STARRUSH
                          (UID             TEXT   NOT NULL,
                           NUM             INT    NOT NULL,
                           PRIMARY KEY(UID));"""
            )
        except:
            raise Exception('创建表发生错误')

    def _create_table_map_refresh(self):
        try:
            self._connect().execute(
                """CREATE TABLE IF NOT EXISTS MAP_REFRESH
                          (DIQU             TEXT   NOT NULL,
                           DIDIAN           TEXT   NOT NULL,
                           POKEMON          TEXT   NOT NULL,
                           PRIMARY KEY(DIQU));"""
            )
        except:
            raise Exception('创建表发生错误')

    def _create_table_refresh_send(self):
        try:
            self._connect().execute(
                """CREATE TABLE IF NOT EXISTS REFRESH_SEND
                          (GROUPID          TEXT   NOT NULL,
                           BOTID            TEXT   NOT NULL,
                           PRIMARY KEY(GROUPID));"""
            )
        except:
            raise Exception('创建表发生错误')

    def _create_table_exchange(self):
        try:
            self._connect().execute(
                """CREATE TABLE IF NOT EXISTS PROP_EXCHANGE
                          (EXCHANGEID       TEXT   NOT NULL,
                           PROPTYPE         TEXT   NOT NULL,
                           PROPNAME         TEXT   NOT NULL,
                           NUM              TEXT   NOT NULL,
                           UID              TEXT   NOT NULL,
                           SCORE            INT    NOT NULL,
                           UPTIME           INT    NOT NULL,
                           PRIMARY KEY(EXCHANGEID));"""
            )
        except:
            raise Exception('创建表发生错误')

    def _create_table_technical(self):
        try:
            self._connect().execute(
                """CREATE TABLE IF NOT EXISTS PROP_TECHNICAL
                          (UID             TEXT   NOT NULL,
                           PROP            TEXT   NOT NULL,
                           NUM             INT    NOT NULL,
                           PRIMARY KEY(UID, PROP));"""
            )
        except:
            raise Exception('创建表发生错误')

    def _create_table_boss_fight(self):
        try:
            self._connect().execute(
                """CREATE TABLE IF NOT EXISTS BOSS_FIGHT
                          (UID             TEXT   NOT NULL,
                           SHANGHAI        INT   NOT NULL,
                           TIME            INT   NOT NULL,
                           PRIMARY KEY(UID,TIME));"""
            )
        except:
            raise Exception('创建表发生错误')

    def _create_table_chongsheng_num(self):
        try:
            self._connect().execute(
                """CREATE TABLE IF NOT EXISTS CHONGSHENG
                          (UID             TEXT   NOT NULL,
                           BIANHAO        INT    NOT NULL,
                           NUM             INT    NOT NULL,
                           PRIMARY KEY(UID,BIANHAO));"""
            )
        except:
            raise Exception('创建表发生错误')

    def _create_table_pipei_table(self):
        try:
            self._connect().execute(
                """CREATE TABLE IF NOT EXISTS POKE_PIPEI
                          (UID             TEXT   NOT NULL,
                           FLAG            INT    NOT NULL,
                           FIGHTID         TEXT   NOT NULL,
                           DIUID           TEXT   NOT NULL,
                           FIGHTTYPE       INT    NOT NULL,
                           PRIMARY KEY(UID));"""
            )
        except:
            raise Exception('创建表发生错误')

    def _create_table_dungeon(self):
        try:
            self._connect().execute(
                """CREATE TABLE IF NOT EXISTS POKE_DUNGEON
                          (UID             TEXT   NOT NULL,
                           NUM             INT    NOT NULL,
                           PRIMARY KEY(UID));"""
            )
        except:
            raise Exception('创建表发生错误')

    def _create_mapauto_add(self):
        with self._connect() as conn:
            r = conn.execute("select sql from sqlite_master where type='table' and name='POKEMON_MAP';").fetchall()
            if 'AUTOFLAG' not in str(r):
                conn.execute("ALTER TABLE POKEMON_MAP ADD AUTOFLAG INT DEFAULT 0;").fetchall()
                conn.execute("ALTER TABLE POKEMON_MAP ADD AUTOTIME INT DEFAULT 0;").fetchall()

    def _create_map_pipei_add(self):
        with self._connect() as conn:
            r = conn.execute("select sql from sqlite_master where type='table' and name='POKEMON_MAP';").fetchall()
            if 'PIPEI' not in str(r):
                period = 0
                conn.execute(f"ALTER TABLE POKEMON_MAP ADD PIPEI INT DEFAULT {period};").fetchall()

    def _create_poketable_add(self):
        with self._connect() as conn:
            r = conn.execute("select sql from sqlite_master where type='table' and name='POKEMON_TABLE';").fetchall()
            if 'XIEDAI' not in str(r):
                conn.execute("ALTER TABLE POKEMON_TABLE ADD XIEDAI TEXT DEFAULT '';").fetchall()

    def _truncate_table_pipei(self):
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM POKE_PIPEI WHERE UID <>''"
            )

    async def _new_dungeon_info(self, uid):
        await execute(
            "insert into poke_dungeon (uid,num) values (?,?) on conflict (uid) do nothing",
            (_text(uid), 0),
        )

    async def update_dungeon(self, uid, dungeonnum):
        await execute(
            "update poke_dungeon set num=? where uid=?",
            (_int(dungeonnum), _text(uid)),
        )

    async def get_dungeon_info(self, uid):
        row = await fetchone(
            "select num from poke_dungeon where uid=?",
            (_text(uid),),
        )
        if row:
            return int(row[0])
        await self._new_dungeon_info(uid)
        return 0

    async def get_dungeon_list(self):
        rows = await fetchall(
            "select uid,num from poke_dungeon where num>0 order by num desc limit ? offset ?",
            (30, 0),
        )
        return rows if rows else 0

    async def _new_pipei_info(self, uid):
        await execute(
            "insert into poke_pipei (uid,flag,fightid,diuid,fighttype) values (?,?,?,?,?) "
            "on conflict (uid) do update set flag=excluded.flag, fightid=excluded.fightid, "
            "diuid=excluded.diuid, fighttype=excluded.fighttype",
            (_text(uid), 0, "0", "0", 0),
        )

    async def update_pipei_flag(self, uid, diuid, fightid):
        await execute(
            "insert into poke_pipei (uid,flag,fightid,diuid,fighttype) values (?,?,?,?,?) "
            "on conflict (uid) do update set flag=excluded.flag, fightid=excluded.fightid, "
            "diuid=excluded.diuid, fighttype=excluded.fighttype",
            (_text(uid), 1, _text(fightid), _text(diuid), 0),
        )

    async def update_pipei_fight(self, uid, fighttype):
        await execute(
            "update poke_pipei set fighttype=? where uid=?",
            (_int(fighttype), _text(uid)),
        )

    async def delete_pipei_uid(self, uid):
        await execute("delete from poke_pipei where uid=?", (_text(uid),))

    async def get_pipei_list(self, uid):
        rows = await fetchall(
            "select uid from poke_pipei where flag=? and uid<>?",
            (0, _text(uid)),
        )
        return rows if rows else 0

    async def get_pipei_info(self, uid):
        row = await fetchone(
            "select flag,fightid,diuid,fighttype from poke_pipei where uid=?",
            (_text(uid),),
        )
        return row if row else 0

    async def _new_chongsheng_num(self, uid, bianhao):
        # 旧逻辑在达成奖励后把计数重置为 0，这里保持 replace 语义。
        await execute(
            "insert into chongsheng (uid,bianhao,num) values (?,?,?) "
            "on conflict (uid,bianhao) do update set num=excluded.num",
            (_text(uid), _int(bianhao), 0),
        )

    async def get_chongsheng_num(self, uid, bianhao):
        row = await fetchone(
            "select num from chongsheng where uid=? and bianhao=?",
            (_text(uid), _int(bianhao)),
        )
        if row:
            return int(row[0])
        await self._new_chongsheng_num(uid, bianhao)
        return 0

    async def update_chongsheng(self, uid, bianhao, num):
        row = await execute_returning(
            "insert into chongsheng (uid,bianhao,num) values (?,?,?) "
            "on conflict (uid,bianhao) do update set num=chongsheng.num+excluded.num returning num",
            (_text(uid), _int(bianhao), _int(num)),
        )
        return int(row[0]) if row else 0

    async def get_boss_shanghai(self, uid, week):
        row = await fetchone(
            "select shanghai from boss_fight where uid=? and time=?",
            (_text(uid), _int(week)),
        )
        return int(row[0]) if row else 0

    async def _new_boss_shanghai(self, uid, shanghai, week):
        expression = (
            "greatest(boss_fight.shanghai, excluded.shanghai)"
            if is_postgres()
            else "max(boss_fight.shanghai, excluded.shanghai)"
        )
        await execute(
            "insert into boss_fight (uid,shanghai,time) values (?,?,?) "
            f"on conflict (uid,time) do update set shanghai={expression}",
            (_text(uid), _int(shanghai), _int(week)),
        )

    async def get_boss_shanghai_list(self, week):
        rows = await fetchall(
            "select uid,shanghai from boss_fight where time=? "
            "order by cast(shanghai as numeric) desc limit ? offset ?",
            (_int(week), 50, 0),
        )
        return rows if rows else 0

    async def get_game_user_list(self):
        rows = await fetchall("select uid from pokemon_map where cast(huizhang as bigint)>0")
        return rows if rows else 0

    async def get_pokemon_technical_list(self, uid, page=0):
        num = 30
        startnum = num * int(page)
        rows = await fetchall(
            "select prop,num from prop_technical where uid=? and num>0 "
            "order by num desc limit ? offset ?",
            (_text(uid), num, startnum),
        )
        if not rows:
            return 0, 0
        count_row = await fetchone(
            "select count(prop) as propnum from prop_technical where uid=? and num>0",
            (_text(uid),),
        )
        total = int(count_row[0]) if count_row else 0
        return total, rows

    async def _new_pokemon_technical(self, uid, propname):
        await execute(
            "insert into prop_technical (uid,prop,num) values (?,?,?) "
            "on conflict (uid,prop) do nothing",
            (_text(uid), _text(propname), 0),
        )

    async def _get_pokemon_technical(self, uid, propname):
        row = await fetchone(
            "select num from prop_technical where uid=? and prop=?",
            (_text(uid), _text(propname)),
        )
        if row:
            return int(row[0])
        await self._new_pokemon_technical(uid, propname)
        return 0

    async def _add_pokemon_technical(self, uid, propname, num):
        await execute(
            "insert into prop_technical (uid,prop,num) values (?,?,?) "
            "on conflict (uid,prop) do update set num=prop_technical.num+excluded.num",
            (_text(uid), _text(propname), _int(num)),
        )

    async def delete_technical_uid(self, uid):
        await execute("delete from prop_technical where uid=?", (_text(uid),))

    async def change_technical_uid(self, newuid, olduid):
        await execute(
            "update prop_technical set uid=? where uid=?",
            (_text(newuid), _text(olduid)),
        )

    async def new_exchange(self, exchangeid, proptype, propname, num, uid, score, uptime):
        await execute(
            "insert into prop_exchange (exchangeid,proptype,propname,num,uid,score,uptime) "
            "values (?,?,?,?,?,?,?) on conflict (exchangeid) do update set "
            "proptype=excluded.proptype, propname=excluded.propname, num=excluded.num, "
            "uid=excluded.uid, score=excluded.score, uptime=excluded.uptime",
            (
                _text(exchangeid),
                _text(proptype),
                _text(propname),
                _int(num),
                _text(uid),
                _int(score),
                _int(uptime),
            ),
        )

    async def update_exchange(self, exchangeid, num):
        # 旧 SQLite 中 NUM 是 TEXT；显式 CAST 让 PG/SQLite 都能做原子加法。
        await execute(
            "update prop_exchange set num=cast(num as bigint)+? where exchangeid=?",
            (_int(num), _text(exchangeid)),
        )

    async def _get_exchange_num(self, exchangeid):
        row = await fetchone(
            "select num from prop_exchange where exchangeid=?",
            (_text(exchangeid),),
        )
        return row[0] if row else 0

    async def _get_exchange_info(self, exchangeid):
        row = await fetchone(
            "select proptype,propname,num,uid,score from prop_exchange where exchangeid=?",
            (_text(exchangeid),),
        )
        return row if row else 0

    async def delete_exchange(self, exchangeid):
        await execute("delete from prop_exchange where exchangeid=?", (_text(exchangeid),))

    async def delete_exchange_uid(self, uid):
        await execute("delete from prop_exchange where uid=?", (_text(uid),))

    async def change_exchange_uid(self, newuid, olduid):
        await execute(
            "update prop_exchange set uid=? where uid=?",
            (_text(newuid), _text(olduid)),
        )

    async def get_exchange_list(self, page=0):
        num = 30
        startnum = num * int(page)
        rows = await fetchall(
            "select exchangeid,proptype,propname,num,score from prop_exchange "
            "where cast(num as bigint)>0 order by propname asc,score asc limit ? offset ?",
            (num, startnum),
        )
        if not rows:
            return 0, 0
        count_row = await fetchone(
            "select count(exchangeid) as exchangenum from prop_exchange where cast(num as bigint)>0"
        )
        total = int(count_row[0]) if count_row else 0
        return total, rows

    async def get_exchange_list_my(self, uid, page=0):
        num = 30
        startnum = num * int(page)
        rows = await fetchall(
            "select exchangeid,proptype,propname,num,score from prop_exchange "
            "where cast(num as bigint)>0 and uid=? order by propname asc,score asc limit ? offset ?",
            (_text(uid), num, startnum),
        )
        if not rows:
            return 0, 0
        count_row = await fetchone(
            "select count(exchangeid) as exchangenum from prop_exchange "
            "where cast(num as bigint)>0 and uid=?",
            (_text(uid),),
        )
        total = int(count_row[0]) if count_row else 0
        return total, rows

    async def get_exchange_list_sx_type(self, proptype, page=0):
        num = 30
        startnum = num * int(page)
        rows = await fetchall(
            "select exchangeid,proptype,propname,num,score from prop_exchange "
            "where cast(num as bigint)>0 and proptype=? "
            "order by propname asc,score asc limit ? offset ?",
            (_text(proptype), num, startnum),
        )
        if not rows:
            return 0, 0
        count_row = await fetchone(
            "select count(exchangeid) as exchangenum from prop_exchange "
            "where cast(num as bigint)>0 and proptype=?",
            (_text(proptype),),
        )
        total = int(count_row[0]) if count_row else 0
        return total, rows

    async def get_exchange_list_sx_name(self, proptype, propname, page=0):
        num = 30
        startnum = num * int(page)
        rows = await fetchall(
            "select exchangeid,proptype,propname,num,score from prop_exchange "
            "where cast(num as bigint)>0 and proptype=? and propname=? "
            "order by propname asc,score asc limit ? offset ?",
            (_text(proptype), _text(propname), num, startnum),
        )
        if not rows:
            return 0, 0
        count_row = await fetchone(
            "select count(exchangeid) as exchangenum from prop_exchange "
            "where cast(num as bigint)>0 and proptype=? and propname=?",
            (_text(proptype), _text(propname)),
        )
        total = int(count_row[0]) if count_row else 0
        return total, rows

    async def get_exchange_list_time(self, findtime):
        rows = await fetchall(
            "select exchangeid,proptype,propname,num,uid from prop_exchange where uptime<?",
            (_int(findtime),),
        )
        return rows if rows else 0

    async def update_refresh_send(self, groupid, botid):
        await execute(
            "insert into refresh_send (groupid,botid) values (?,?) "
            "on conflict (groupid) do update set botid=excluded.botid",
            (_text(groupid), _text(botid)),
        )

    async def get_refresh_send_list(self):
        rows = await fetchall("select groupid,botid from refresh_send")
        return rows if rows else 0

    async def delete_refresh_send(self, groupid):
        await execute("delete from refresh_send where groupid=?", (_text(groupid),))

    async def update_map_refresh(self, diqu, didian, pokemon):
        await execute(
            "insert into map_refresh (diqu,didian,pokemon) values (?,?,?) "
            "on conflict (diqu) do update set didian=excluded.didian, pokemon=excluded.pokemon",
            (_text(diqu), _text(didian), _text(pokemon)),
        )

    async def get_map_refresh(self, diqu, didian):
        row = await fetchone(
            "select pokemon from map_refresh where diqu=? and didian=?",
            (_text(diqu), _text(didian)),
        )
        return row[0] if row else 0

    async def get_map_refresh_list(self):
        rows = await fetchall("select diqu,didian,pokemon from map_refresh")
        return rows if rows else 0

    async def update_pokemon_star(self, uid, bianhao, startype=0):
        await execute(
            "insert into pokemon_star (uid,bianhao,type) values (?,?,?) "
            "on conflict (uid,bianhao) do update set type=excluded.type",
            (_text(uid), _int(bianhao), _int(startype)),
        )

    async def get_pokemon_star(self, uid, bianhao):
        row = await fetchone(
            "select type from pokemon_star where uid=? and bianhao=?",
            (_text(uid), _int(bianhao)),
        )
        return int(row[0]) if row else 0

    async def _delete_poke_star(self, uid):
        await execute("delete from pokemon_star where uid=?", (_text(uid),))

    async def _change_poke_star(self, newuid, olduid):
        await execute(
            "update pokemon_star set uid=? where uid=?",
            (_text(newuid), _text(olduid)),
        )

    async def _delete_poke_starrush_uid(self, uid):
        await execute("delete from pokemon_starrush where uid=?", (_text(uid),))

    async def _change_poke_starrush_uid(self, newuid, olduid):
        await execute(
            "update pokemon_starrush set uid=? where uid=?",
            (_text(newuid), _text(olduid)),
        )

    async def _delete_poke_star_bianhao(self, uid, bianhao):
        await execute(
            "delete from pokemon_star where uid=? and bianhao=?",
            (_text(uid), _int(bianhao)),
        )

    async def get_pokemon_starrush(self, uid):
        row = await fetchone(
            "select num from pokemon_starrush where uid=?",
            (_text(uid),),
        )
        if row:
            return int(row[0])
        await self.new_pokemon_starrush(uid)
        return 0

    async def update_pokemon_starrush(self, uid, num):
        await execute(
            "insert into pokemon_starrush (uid,num) values (?,?) "
            "on conflict (uid) do update set num=pokemon_starrush.num+excluded.num",
            (_text(uid), _int(num)),
        )

    async def new_pokemon_starrush(self, uid):
        await execute(
            "insert into pokemon_starrush (uid,num) values (?,?) "
            "on conflict (uid) do update set num=excluded.num",
            (_text(uid), 0),
        )

    async def get_pokemon_prop_list(self, uid):
        rows = await fetchall(
            "select prop,num from pokemon_prop where uid=? and num>0 order by num",
            (_text(uid),),
        )
        return rows if rows else 0

    async def _new_pokemon_prop(self, uid, propname):
        await execute(
            "insert into pokemon_prop (uid,prop,num) values (?,?,?) "
            "on conflict (uid,prop) do nothing",
            (_text(uid), _text(propname), 0),
        )

    async def _get_pokemon_prop(self, uid, propname):
        row = await fetchone(
            "select num from pokemon_prop where uid=? and prop=?",
            (_text(uid), _text(propname)),
        )
        if row:
            return int(row[0])
        await self._new_pokemon_prop(uid, propname)
        return 0

    async def _add_pokemon_prop(self, uid, propname, num):
        await execute(
            "insert into pokemon_prop (uid,prop,num) values (?,?,?) "
            "on conflict (uid,prop) do update set num=pokemon_prop.num+excluded.num",
            (_text(uid), _text(propname), _int(num)),
        )

    async def delete_pokemon_prop(self, uid):
        await execute("delete from pokemon_prop where uid=?", (_text(uid),))

    async def change_pokemon_prop(self, newuid, olduid):
        await execute(
            "update pokemon_prop set uid=? where uid=?",
            (_text(newuid), _text(olduid)),
        )

    async def _add_pokemon_group(self, uid, pokemon_list):
        await execute(
            "insert into pokemon_team (uid,team) values (?,?) "
            "on conflict (uid) do update set team=excluded.team",
            (_text(uid), _text(pokemon_list)),
        )

    async def get_pokemon_group(self, uid):
        row = await fetchone("select team from pokemon_team where uid=?", (_text(uid),))
        return row[0] if row else ""

    async def delete_pokemon_group(self, uid):
        await execute("delete from pokemon_team where uid=?", (_text(uid),))

    async def change_pokemon_group(self, newuid, olduid):
        await execute(
            "update pokemon_team set uid=? where uid=?",
            (_text(newuid), _text(olduid)),
        )

    async def _add_pokemon_egg(self, uid, bianhao, use_num):
        await execute(
            "insert into pokemon_egg (uid,bianhao,num) values (?,?,?) "
            "on conflict (uid,bianhao) do update set num=pokemon_egg.num+excluded.num",
            (_text(uid), _int(bianhao), _int(use_num)),
        )

    async def delete_pokemon_egg_bianhao(self, uid, bianhao):
        await execute(
            "update pokemon_egg set num=? where uid=? and bianhao=?",
            (0, _text(uid), _int(bianhao)),
        )

    async def update_pokemon_egg_bianhao(self, uid, bianhao, egg_num):
        await execute(
            "update pokemon_egg set num=? where uid=? and bianhao=?",
            (_int(egg_num), _text(uid), _int(bianhao)),
        )

    async def get_pokemon_egg(self, uid, bianhao):
        row = await fetchone(
            "select num from pokemon_egg where uid=? and bianhao=?",
            (_text(uid), _int(bianhao)),
        )
        return int(row[0]) if row else 0

    async def get_pokemon_egg_num(self, uid):
        row = await fetchone(
            "select count(bianhao) as eggnum from pokemon_egg where uid=? and num>0",
            (_text(uid),),
        )
        return int(row[0]) if row else 0

    async def get_pokemon_egg_list(self, uid, page=0):
        num = 30
        startnum = num * int(page)
        rows = await fetchall(
            "select bianhao,num from pokemon_egg where uid=? and num>0 "
            "order by num desc,bianhao asc limit ? offset ?",
            (_text(uid), num, startnum),
        )
        return rows if rows else 0

    async def delete_pokemon_egg(self, uid):
        await execute("delete from pokemon_egg where uid=?", (_text(uid),))

    async def change_pokemon_egg(self, newuid, olduid):
        await execute(
            "update pokemon_egg set uid=? where uid=?",
            (_text(newuid), _text(olduid)),
        )

    async def _get_map_now(self, uid):
        row = await fetchone(
            "select huizhang,map_name,nickname,pipei,autoflag,autotime "
            "from pokemon_map where uid=?",
            (_text(uid),),
        )
        return row if row else [0, "", 0, 0]

    async def _get_map_info_nickname(self, nickname):
        row = await fetchone(
            "select huizhang,map_name,uid,pipei,autoflag,autotime "
            "from pokemon_map where nickname=?",
            (_text(nickname),),
        )
        return row if row else [0, "", 0, 0]

    async def _add_map_now(self, uid, map_name):
        await execute(
            "update pokemon_map set map_name=? where uid=?",
            (_text(map_name), _text(uid)),
        )

    async def _new_map_info(self, uid, map_name, nickname):
        await execute(
            "insert into pokemon_map (uid,huizhang,map_name,nickname,pipei,autoflag,autotime) "
            "values (?,?,?,?,?,?,?) on conflict (uid) do update set "
            "huizhang=excluded.huizhang, map_name=excluded.map_name, "
            "nickname=excluded.nickname, pipei=excluded.pipei, "
            "autoflag=excluded.autoflag, autotime=excluded.autotime",
            (_text(uid), 0, _text(map_name), _text(nickname), 0, 0, 0),
        )

    async def get_map_pipei_num(self, uid):
        row = await fetchone(
            "select pipei from pokemon_map where uid=?",
            (_text(uid),),
        )
        return int(row[0]) if row else 0

    async def get_map_pipei_list(self):
        rows = await fetchall("select uid,pipei from pokemon_map where pipei>0")
        return rows if rows else 0

    async def update_map_pipei(self, uid, pipei_num):
        await execute(
            "update pokemon_map set pipei=? where uid=?",
            (_int(pipei_num), _text(uid)),
        )

    async def update_map_pipei_num(self, uid, pipei):
        expression = _clamp_zero("pipei+?")
        await execute(
            f"update pokemon_map set pipei={expression} where uid=?",
            (_int(pipei), _text(uid)),
        )

    async def update_map_autoinfo(self, uid, autoflag, autotime):
        await execute(
            "update pokemon_map set autoflag=?, autotime=? where uid=?",
            (_int(autoflag), _int(autotime), _text(uid)),
        )

    async def _update_map_name(self, uid, nickname):
        await execute(
            "update pokemon_map set nickname=? where uid=?",
            (_text(nickname), _text(uid)),
        )

    async def _update_map_huizhang(self, uid, huizhang):
        await execute(
            "update pokemon_map set huizhang=? where uid=?",
            (_int(huizhang), _text(uid)),
        )

    async def delete_pokemon_map(self, uid):
        await execute("delete from pokemon_map where uid=?", (_text(uid),))

    async def change_pokemon_map(self, newuid, olduid):
        await execute(
            "update pokemon_map set uid=? where uid=?",
            (_text(newuid), _text(olduid)),
        )

    async def _add_huizhang_now(self, uid, huizhang):
        await execute(
            "update pokemon_map set huizhang=? where uid=?",
            (_text(huizhang), _text(uid)),
        )

    async def _add_pokemon_info(self, uid, bianhao, pokemon_info, exp=0):
        (
            level,
            gt_hp,
            gt_atk,
            gt_def,
            gt_stk,
            gt_sdf,
            gt_spd,
            nl_hp,
            nl_atk,
            nl_def,
            nl_stk,
            nl_sef,
            nl_spd,
            xingge,
            jineng,
            _newexp,
            xiedai,
        ) = pokemon_info
        await execute(
            "insert into pokemon_table "
            "(uid,bianhao,level,exp,gt_hp,gt_atk,gt_def,gt_stk,gt_sef,gt_spd,"
            "nl_hp,nl_atk,nl_def,nl_stk,nl_sef,nl_spd,xingge,jineng,xiedai) "
            "values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
            "on conflict (uid,bianhao) do update set "
            "level=excluded.level, exp=excluded.exp, gt_hp=excluded.gt_hp, "
            "gt_atk=excluded.gt_atk, gt_def=excluded.gt_def, gt_stk=excluded.gt_stk, "
            "gt_sef=excluded.gt_sef, gt_spd=excluded.gt_spd, nl_hp=excluded.nl_hp, "
            "nl_atk=excluded.nl_atk, nl_def=excluded.nl_def, nl_stk=excluded.nl_stk, "
            "nl_sef=excluded.nl_sef, nl_spd=excluded.nl_spd, xingge=excluded.xingge, "
            "jineng=excluded.jineng, xiedai=excluded.xiedai",
            (
                _text(uid),
                _int(bianhao),
                _int(level),
                _int(exp),
                _int(gt_hp),
                _int(gt_atk),
                _int(gt_def),
                _int(gt_stk),
                _int(gt_sdf),
                _int(gt_spd),
                _int(nl_hp),
                _int(nl_atk),
                _int(nl_def),
                _int(nl_stk),
                _int(nl_sef),
                _int(nl_spd),
                _text(xingge),
                _text(jineng),
                _text(xiedai),
            ),
        )

    async def _add_pokemon_level(self, uid, bianhao, level, exp):
        await execute(
            "update pokemon_table set level=?, exp=? where uid=? and bianhao=?",
            (_int(level), _int(exp), _text(uid), _int(bianhao)),
        )

    async def _add_pokemon_nuli(
        self, uid, bianhao, nl_hp, nl_atk, nl_def, nl_stk, nl_sef, nl_spd
    ):
        await execute(
            "update pokemon_table set nl_hp=?,nl_atk=?,nl_def=?,nl_stk=?,nl_sef=?,nl_spd=? "
            "where uid=? and bianhao=?",
            (
                _int(nl_hp),
                _int(nl_atk),
                _int(nl_def),
                _int(nl_stk),
                _int(nl_sef),
                _int(nl_spd),
                _text(uid),
                _int(bianhao),
            ),
        )

    async def _add_pokemon_jineng(self, uid, bianhao, jineng):
        await execute(
            "update pokemon_table set jineng=? where uid=? and bianhao=?",
            (_text(jineng), _text(uid), _int(bianhao)),
        )

    async def _add_pokemon_xiedai(self, uid, bianhao, xiedai):
        await execute(
            "update pokemon_table set xiedai=? where uid=? and bianhao=?",
            (_text(xiedai), _text(uid), _int(bianhao)),
        )

    async def _add_pokemon_xingge(self, uid, bianhao, xingge):
        await execute(
            "update pokemon_table set xingge=? where uid=? and bianhao=?",
            (_text(xingge), _text(uid), _int(bianhao)),
        )

    async def _add_pokemon_id(self, uid, bianhao, changeid):
        await execute(
            "update pokemon_table set bianhao=? where uid=? and bianhao=?",
            (_int(changeid), _text(uid), _int(bianhao)),
        )

    async def _get_pokemon_info(self, uid, bianhao):
        row = await fetchone(
            "select level,gt_hp,gt_atk,gt_def,gt_stk,gt_sef,gt_spd,"
            "nl_hp,nl_atk,nl_def,nl_stk,nl_sef,nl_spd,xingge,jineng,exp,xiedai "
            "from pokemon_table where uid=? and bianhao=?",
            (_text(uid), _int(bianhao)),
        )
        return row if row else 0

    async def _get_pokemon_info_list(self, bianhao):
        rows = await fetchall(
            "select uid,(gt_hp+gt_atk+gt_def+gt_sef+gt_spd+gt_stk) as gt_z "
            "from pokemon_table where bianhao=? "
            "order by (gt_hp+gt_atk+gt_def+gt_sef+gt_spd+gt_stk) desc limit ? offset ?",
            (_int(bianhao), 50, 0),
        )
        return rows if rows else 0

    async def _get_pokemon_info_list_pm(self, uid):
        rows = await fetchall(
            "select bianhao,(gt_hp+gt_atk+gt_def+gt_sef+gt_spd+gt_stk) as gt_z "
            "from pokemon_table where uid=? "
            "order by (gt_hp+gt_atk+gt_def+gt_sef+gt_spd+gt_stk) desc limit ? offset ?",
            (_text(uid), 50, 0),
        )
        return rows if rows else 0

    async def _get_pokemon_level(self, uid, bianhao):
        row = await fetchone(
            "select level,exp from pokemon_table where uid=? and bianhao=?",
            (_text(uid), _int(bianhao)),
        )
        return row if row else 0

    async def _get_pokemon_num(self, uid):
        row = await fetchone(
            "select count(bianhao) as num from pokemon_table where uid=?",
            (_text(uid),),
        )
        return int(row[0]) if row else 0

    async def _get_pokemon_list(self, uid, page=0):
        num = 30
        startnum = num * int(page)
        rows = await fetchall(
            "select bianhao,level from pokemon_table where uid=? "
            "order by level desc,bianhao asc limit ? offset ?",
            (_text(uid), num, startnum),
        )
        return rows if rows else 0

    async def _get_my_pokemon(self, uid):
        rows = await fetchall(
            "select bianhao from pokemon_table where uid=? order by level desc",
            (_text(uid),),
        )
        return rows if rows else 0

    async def _delete_poke_info(self, uid):
        await execute("delete from pokemon_table where uid=?", (_text(uid),))

    async def _change_poke_info(self, newuid, olduid):
        await execute(
            "update pokemon_table set uid=? where uid=?",
            (_text(newuid), _text(olduid)),
        )

    async def _delete_poke_bianhao(self, uid, bianhao):
        await execute(
            "delete from pokemon_table where uid=? and bianhao=?",
            (_text(uid), _int(bianhao)),
        )

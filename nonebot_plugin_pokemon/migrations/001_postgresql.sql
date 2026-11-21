-- Owned by the Qiqi game plugins in the QWeb PostgreSQL database.
CREATE SCHEMA qiqi_pokemon;

CREATE TABLE qiqi_pokemon.boss_fight (
    uid text NOT NULL,
    shanghai bigint NOT NULL,
    time bigint NOT NULL,
    PRIMARY KEY (uid, time)
);

CREATE TABLE qiqi_pokemon.chongsheng (
    uid text NOT NULL,
    bianhao bigint NOT NULL,
    num bigint NOT NULL,
    PRIMARY KEY (uid, bianhao)
);

CREATE TABLE qiqi_pokemon.map_refresh (
    diqu text NOT NULL,
    didian text NOT NULL,
    pokemon text NOT NULL,
    PRIMARY KEY (diqu)
);

CREATE TABLE qiqi_pokemon.pokemon_egg (
    uid text NOT NULL,
    bianhao bigint NOT NULL,
    num bigint NOT NULL,
    PRIMARY KEY (uid, bianhao)
);

CREATE TABLE qiqi_pokemon.pokemon_game (
    uid text NOT NULL,
    type text NOT NULL,
    num bigint NOT NULL,
    PRIMARY KEY (uid, type)
);

CREATE TABLE qiqi_pokemon.pokemon_map (
    uid text NOT NULL,
    huizhang text NOT NULL,
    map_name text NOT NULL,
    nickname text NOT NULL,
    pipei bigint DEFAULT 0,
    autoflag bigint DEFAULT 0,
    autotime bigint DEFAULT 0,
    PRIMARY KEY (uid)
);

CREATE TABLE qiqi_pokemon.pokemon_prop (
    uid text NOT NULL,
    prop text NOT NULL,
    num bigint NOT NULL,
    PRIMARY KEY (uid, prop)
);

CREATE TABLE qiqi_pokemon.pokemon_score (
    uid text NOT NULL,
    score bigint NOT NULL,
    shengwang bigint NOT NULL,
    PRIMARY KEY (uid)
);

CREATE TABLE qiqi_pokemon.pokemon_star (
    uid text NOT NULL,
    bianhao bigint NOT NULL,
    type bigint NOT NULL,
    PRIMARY KEY (uid, bianhao)
);

CREATE TABLE qiqi_pokemon.pokemon_starrush (
    uid text NOT NULL,
    num bigint NOT NULL,
    PRIMARY KEY (uid)
);

CREATE TABLE qiqi_pokemon.pokemon_table (
    uid text NOT NULL,
    bianhao bigint NOT NULL,
    level bigint NOT NULL,
    exp bigint NOT NULL,
    gt_hp bigint NOT NULL,
    gt_atk bigint NOT NULL,
    gt_def bigint NOT NULL,
    gt_stk bigint NOT NULL,
    gt_sef bigint NOT NULL,
    gt_spd bigint NOT NULL,
    nl_hp bigint NOT NULL,
    nl_atk bigint NOT NULL,
    nl_def bigint NOT NULL,
    nl_stk bigint NOT NULL,
    nl_sef bigint NOT NULL,
    nl_spd bigint NOT NULL,
    xingge text NOT NULL,
    jineng text NOT NULL,
    xiedai text DEFAULT '',
    PRIMARY KEY (uid, bianhao)
);

CREATE TABLE qiqi_pokemon.pokemon_team (
    uid text NOT NULL,
    team text NOT NULL,
    PRIMARY KEY (uid)
);

CREATE TABLE qiqi_pokemon.poke_dungeon (
    uid text NOT NULL,
    num bigint NOT NULL,
    PRIMARY KEY (uid)
);

CREATE TABLE qiqi_pokemon.poke_pipei (
    uid text NOT NULL,
    flag bigint NOT NULL,
    fightid text NOT NULL,
    diuid text NOT NULL,
    fighttype bigint NOT NULL,
    PRIMARY KEY (uid)
);

CREATE TABLE qiqi_pokemon.prop_exchange (
    exchangeid text NOT NULL,
    proptype text NOT NULL,
    propname text NOT NULL,
    num text NOT NULL,
    uid text NOT NULL,
    score bigint NOT NULL,
    uptime bigint NOT NULL,
    PRIMARY KEY (exchangeid)
);

CREATE TABLE qiqi_pokemon.prop_technical (
    uid text NOT NULL,
    prop text NOT NULL,
    num bigint NOT NULL,
    PRIMARY KEY (uid, prop)
);

CREATE TABLE qiqi_pokemon.refresh_send (
    groupid text NOT NULL,
    botid text NOT NULL,
    PRIMARY KEY (groupid)
);

CREATE TABLE qiqi_pokemon.limiter (
    key text NOT NULL,
    num bigint NOT NULL,
    date bigint,
    PRIMARY KEY (key)
);

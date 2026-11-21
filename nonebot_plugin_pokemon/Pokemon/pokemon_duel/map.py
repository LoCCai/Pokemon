import re
import random
import math
import copy
import time
from PIL import Image, ImageDraw
from nonebot_plugin_pokemon.compat.media import open_image
from nonebot_plugin_pokemon.compat.sv import SV
from nonebot_plugin_pokemon.compat.models import Event
import pytz
from collections import Counter
from nonebot_plugin_pokemon.compat.segment import MessageSegment
from nonebot_plugin_pokemon.compat.gss import gss
from nonebot_plugin_pokemon.compat.image import convert_img
from ..utils.resource.RESOURCE_PATH import CHAR_ICON_PATH
from nonebot_plugin_pokemon.compat.message_models import Button
from nonebot_plugin_pokemon.compat.aps import scheduler
from datetime import datetime
import json
from .pokeconfg import *
from .until import *
from pathlib import Path
from .nameconfig import First_Name, Last_Name, Call_Name
from .draw_image import draw_pokemon_info
from ..utils.fonts.starrail_fonts import (
    sr_font_20,
    sr_font_24,
)

black_color = (0, 0, 0)

class SEND_TIME:
    def __init__(self):
        self.uese_time = {}

    def record_user_time(self, uid, times):
        self.uese_time[uid] = times

    def get_user_time(self, uid):
        return self.uese_time[uid] if self.uese_time.get(uid) is not None else 0

time_send = SEND_TIME()

Excel_path = Path(__file__).parent
with Path.open(Excel_path / 'map.json', encoding='utf-8') as f:
    map_dict = json.load(f)
    diqulist = map_dict['diqulist']
    didianlist = map_dict['didianlist']

TEXT_PATH = Path(__file__).parent / 'texture2D'

ts_prop_list = [
    '体力之羽',
    '肌力之羽',
    '抵抗之羽',
    '智力之羽',
    '精神之羽',
    '瞬发之羽',
    '神奇糖果',
    '榴石果',
    '藻根果',
    '比巴果',
    '哈密果',
    '萄葡果',
    '茄番果',
]

sv_pokemon_map = SV('宝可梦地图', priority=5)
sv_pokemon_tansuo = SV('宝可梦探索', priority=5)
sv_pm_config = SV('宝可梦管理', pm=0)
@sv_pokemon_map.on_fullmatch(['大量出现信息'])
async def get_day_pokemon_refresh(bot, ev: Event):
    refresh_list = await POKE.get_map_refresh_list()
    mes = "当前大量出现信息"
    for refresh in refresh_list:
        pokename = CHARA_NAME[int(refresh[2])][0]
        pokename = pokename.replace(')','）')
        mes += f'\n{CHARA_NAME[int(refresh[2])][0]} 在 {refresh[0]}地区-{refresh[1]}大量出现了'
    buttons = [
        Button('前往', '前往', '前往', action=2),
    ]
    await bot.send_option(mes, buttons)

@sv_pokemon_map.on_command(('替换消息发送方式', '替换发送方式'))
async def show_poke_info(bot, ev: Event):
    args = ev.text.split()
    if len(args) != 1:
        return await bot.send('请输入 替换消息发送方式[图片/文字]。', at_sender=True)
    global TS_PIC
    if args[0] == '图片':
        TS_PIC = 1
    if args[0] == '文字':
        TS_PIC = 0
    await bot.send('消息发送类型已替换')

@sv_pokemon_map.on_fullmatch(['我的金钱'])
async def map_my_score(bot, ev: Event):
    uid = ev.user_id

    my_score = await SCORE.get_score(uid)
    await bot.send(f'您的金钱为{my_score}', at_sender=True)


@sv_pokemon_map.on_prefix(('更新队伍', '新建队伍'))
async def map_my_group(bot, ev: Event):
    args = ev.text.split()
    if len(args) < 1:
        return await bot.send(
            '请输入 更新队伍+宝可梦名称(中间用空格分隔)。', at_sender=True
        )
    if len(args) > 6:
        return await bot.send('一个队伍最多只能有6只宝可梦。', at_sender=True)
    uid = ev.user_id
    pokemon_list = []
    name_str = ''

    for pokemon_name in args:
        bianhao = await get_poke_bianhao(pokemon_name)
        if bianhao == 0:
            return await bot.send('请输入正确的宝可梦名称。', at_sender=True)
        pokemon_info = await get_pokeon_info(uid, bianhao)
        if pokemon_info == 0:
            return await bot.send(
                f'您还没有{CHARA_NAME[bianhao][0]}。', at_sender=True
            )
        if str(bianhao) not in pokemon_list:
            pokemon_list.append(str(bianhao))
            startype = await POKE.get_pokemon_star(uid, bianhao)
            name_str += (
                f' {starlist[startype]}{pokemon_name} Lv.{pokemon_info[0]}\n'
            )
    pokemon_str = ','.join(pokemon_list)
    await POKE._add_pokemon_group(uid, pokemon_str)

    mes = f'编组成功，当前队伍\n{name_str}'
    buttons = [
        Button('🏝️野外探索', '野外探索', '🏝️野外探索', action=1),
    ]
    mapinfo = await POKE._get_map_now(uid)
    huizhang = mapinfo[0]
    if int(huizhang) < 8:
        buttons.append(Button('挑战道馆', '挑战道馆', '挑战道馆', action=1))
    elif int(huizhang) == 8:
        buttons.append(Button('挑战天王', '挑战天王', '挑战天王', action=1))
    elif int(huizhang) == 9:
        buttons.append(Button('挑战冠军', '挑战四天王冠军', '挑战冠军', action=1))
    await bot.send_option(mes, buttons)


@sv_pokemon_map.on_fullmatch(['训练家名片'])
async def map_my_info(bot, ev: Event):
    print(ev)
    uid = ev.user_id

    my_score = await SCORE.get_score(uid)
    my_pokemon = await POKE._get_pokemon_num(uid)
    if my_pokemon == 0:
        return await bot.send(
            '您还没有领取初始精灵成为训练家哦', at_sender=True
        )
    my_team = await POKE.get_pokemon_group(uid)
    pokemon_list = my_team.split(',')
    mapinfo = await POKE._get_map_now(uid)
    name = mapinfo[2]
    mychenghao, huizhang = await get_chenghao(uid)
    buttonlist = ['精灵状态', '我的精灵蛋', '查看地图']
    if name == uid:
        if ev.sender:
            sender = ev.sender
            if sender.get('nickname', '') != '':
                name = sender['nickname']
    myduanwei = await get_now_duanwei(mapinfo[3])
    mes = ''
    mes += f'训练家名称:{name}\n'
    mes += f'训练家称号:{mychenghao}\n'
    mes += f'当前段位:{myduanwei}({mapinfo[3]})\n'
    mes += f'拥有金钱:{my_score}\n'
    mes += f'拥有徽章:{huizhang}\n'
    if mapinfo[1]:
        this_map = mapinfo[1]
        diquname = diqulist[didianlist[this_map]['fname']]['name']
        mes += f'当前所在地:{diquname}-{this_map}\n'
    mes += f'拥有精灵:{my_pokemon}只\n'
    mes += '当前队伍:'
    if my_team:
        for bianhao in pokemon_list:
            bianhao = int(bianhao)
            pokemon_info = await get_pokeon_info(uid, bianhao)
            startype = await POKE.get_pokemon_star(uid, bianhao)
            pokename = CHARA_NAME[bianhao][0]
            if ')' in CHARA_NAME[bianhao][0]:
                pokename = pokename.replace(')','）')
            mes += f'\n{starlist[startype]}{CHARA_NAME[bianhao][0]} Lv.{pokemon_info[0]}'
    buttons = [
        Button('📖精灵状态', '精灵状态', '📖精灵状态', action=2),
        Button('📖我的精灵蛋', '我的精灵蛋', '📖我的精灵蛋', action=1),
        Button('🗺查看地图', '查看地图', '🗺查看地图', action=1),
    ]
    await bot.send_option(mes, buttons)


@sv_pokemon_map.on_prefix(('修改训练家名称', '修改名称'))
async def update_my_name(bot, ev: Event):
    args = ev.text.split()
    if len(args) < 1:
        return await bot.send('请输入 修改训练家名称+昵称。', at_sender=True)
    uid = ev.user_id
    name = args[0]
    if len(name) > 10:
        return await bot.send('昵称长度不能超过10个字符。', at_sender=True)
    if name.isdigit():
        return await bot.send('昵称不能为纯数字。', at_sender=True)
    mapinfo = await POKE._get_map_info_nickname(name)
    if mapinfo[2] == 0:
        await POKE._update_map_name(uid, name)
        await bot.send(f'修改成功，当前训练家名称为 {name}', at_sender=True)
    else:
        return await bot.send(
            '该昵称已被其他玩家抢注，请选择其他昵称。', at_sender=True
        )


@sv_pokemon_map.on_fullmatch(['打工'])
async def map_work_test(bot, ev: Event):
    uid = ev.user_id

    mypokelist = await POKE._get_pokemon_list(uid)
    if mypokelist == 0:
        return await bot.send(
            '您还没有精灵，请输入 领取初始精灵+初始精灵名称 开局。',
            at_sender=True,
        )
    mapinfo = await POKE._get_map_now(uid)
    this_map = mapinfo[1]
    if not daily_work_limiter.check(uid):
        return await bot.send(
            '今天的打工次数已经超过上限了哦，明天再来吧。', at_sender=True
        )
    
    if didianlist[this_map]['type'] == '城镇':
        get_score = (int(mapinfo[0]) + 1) * 5000
        await SCORE.update_score(uid, get_score)
        daily_work_limiter.increase(uid)
        mes = f'您通过打工获得了{get_score}金钱'
        await bot.send(mes, at_sender=True)
    else:
        return await bot.send('该区域无法打工，请返回城镇哦', at_sender=True)

@sv_pokemon_map.on_fullmatch(['开启自动探索'])
async def map_ts_auto_start(bot, ev: Event):
    uid = ev.user_id
    mypokelist = await POKE._get_pokemon_list(uid)
    if mypokelist == 0:
        return await bot.send(
            '您还没有精灵，请输入 领取初始精灵+初始精灵名称 开局。\n初始精灵列表可输入[初始精灵列表]查询',
            at_sender=True,
        )
    mapinfo = await POKE._get_map_now(uid)
    if mapinfo[4] == 1:
        return await bot.send('您已经处于自动探索中了哦~', at_sender=True)
    this_map = mapinfo[1]
    if this_map == '':
        return await bot.send(
            '您还选择初始地区，请输入 选择初始地区+地区名称。', at_sender=True
        )
    my_team = await POKE.get_pokemon_group(uid)
    if my_team == '':
        return await bot.send(
            '您还没有创建队伍，请输入 创建队伍+宝可梦名称(中间用空格分隔)。',
            at_sender=True,
        )
    if didianlist[this_map]['type'] == '城镇' or didianlist[this_map]['type'] == '建筑':
        return await bot.send(
            '您当前所处的地点没有可探索的区域', at_sender=True
        )
    now_time = time.time()
    now_time = math.ceil(now_time)
    await POKE.update_map_autoinfo(uid, 1, now_time)
    return await bot.send('您开始了自动野外探索，自动探索最长时间为24小时哦~', at_sender=True)
    
@sv_pokemon_map.on_fullmatch(('结束自动探索','关闭自动探索'))
async def map_ts_auto_end(bot, ev: Event):
    uid = ev.user_id
    now_time = time.time()
    now_time = math.ceil(now_time)
    mapinfo = await POKE._get_map_now(uid)
    if mapinfo[4] == 0:
        return await bot.send('您没有处于探索中哦~', at_sender=True)
    starttime = mapinfo[5]
    await POKE.update_map_autoinfo(uid, 0, 0)
    this_map = mapinfo[1]
    jiangetime = now_time - starttime
    if jiangetime < 900:
        return await bot.send('自动探索时间小于15分钟，无法获得奖励~', at_sender=True)
    msg = ''
    ts_min_time = math.ceil(jiangetime/60)
    msg += f"探索时长{ts_min_time}分钟\n"
    if jiangetime > 86400:
        msg += f"由于超出24小时，按照24小时结算\n"
        jiangetime = 86400
    
    jiangenum = math.ceil(jiangetime/AUTO_TS_JS)
    
    my_team = await POKE.get_pokemon_group(uid)
    pokemon_team = my_team.split(',')
    mypokelevellist = {}
    mypokelist = []
    mypokeexplist = {}
    for bianhao in pokemon_team:
        bianhao = int(bianhao)
        mypokelist.append(bianhao)
        pokeinfo = await get_pokeon_info(uid, bianhao)
        mypokelevellist[bianhao] = pokeinfo[0]
        mypokeexplist[bianhao] = 0
    msg += "探索结算成功\n"
    ts_z = TS_FIGHT + TS_PROP + TS_POKEMON
    #结算野生训练家战斗
    ts_fight_num = int(jiangenum * TS_FIGHT/ts_z)
    msg += f"遭遇野生训练家{ts_fight_num}次\n"
    pokelist = didianlist[this_map]['pokemon']
    pokenum_fight = 0
    maxnum = min(5, int(didianlist[this_map]['need']) + 1)
    min_level = didianlist[this_map]['level'][0] / 2 + didianlist[this_map]['level'][0]
    max_level = didianlist[this_map]['level'][0] / 2 + didianlist[this_map]['level'][1]
    pokelevel_fight = 0
    for pokename in pokelist:
        pokenum_fight = pokenum_fight + int(math.floor(random.uniform(1, maxnum)))
        pokelevel_fight = pokelevel_fight + int(math.floor(random.uniform(min_level, max_level)))
    fight_num = int(pokenum_fight/len(pokelist)) * ts_fight_num
    fight_level = int(pokelevel_fight/len(pokelist))
    fight_poke_list = copy.deepcopy(pokelist)
    
    sampled_data_fight= random.choices(fight_poke_list, k=fight_num)
    sampled_fight_list = list(sampled_data_fight)
    fight_count = Counter(sampled_fight_list)
    for fight_pokeid in fight_count:
        mypokeexplist = await get_auto_win_exp(fight_level, fight_pokeid, mypokelist, mypokelevellist, mypokeexplist, fight_count[fight_pokeid])
    get_score = (int(didianlist[this_map]['need']) + 1) * 800 * ts_fight_num
    await SCORE.update_score(uid, get_score)
    msg += f"获得金币{get_score}\n"
    
    #结算道具拾取
    ts_prop_num = int(jiangenum * TS_PROP/ts_z)
    msg += f"\n拾取了{ts_prop_num}件道具\n"
    prop_list_ts = copy.deepcopy(ts_prop_list)
    
    sampled_data_prop = random.choices(prop_list_ts, k=ts_prop_num)
    sampled_prop_list = list(sampled_data_prop)
    prop_count = Counter(sampled_prop_list)
    for prop_name in prop_count:
        msg += f"获得了{prop_name}x{prop_count[prop_name]}\n"
        await POKE._add_pokemon_prop(uid, prop_name, prop_count[prop_name])
    
    #结算野生精灵遭遇
    ts_pokemon_num = int(jiangenum * TS_POKEMON/ts_z)
    msg += f"\n遭遇野生精灵{ts_pokemon_num}次\n"
    level_min = didianlist[this_map]['level'][0]
    level_max = didianlist[this_map]['level'][1]
    pokelevel_ys = 0
    pokeqj_num = 0
    for pokename in pokelist:
        pokeqj_num = pokeqj_num + int(math.floor(random.uniform(3, 6)))
        pokelevel_ys = pokelevel_ys + int(math.floor(random.uniform(level_min, level_max)))
    qunju_num = ts_pokemon_num * int(QUN_POKE/100)
    pokefight_num = int(pokenum_fight/len(pokelist)) * qunju_num + (ts_pokemon_num - qunju_num)
    pokefight_level = int(pokelevel_ys/len(pokelist))
    poke_fight_list = copy.deepcopy(pokelist)
    
    sampled_data_poke= random.choices(fight_poke_list, k=pokefight_num)
    sampled_poke_list = list(sampled_data_poke)
    poke_count = Counter(sampled_poke_list)
    get_egg_list = {}
    xuexi_all_list = []
    for fight_poke_id in poke_count:
        xuexi_list = POKEMON_XUEXI[fight_poke_id]
        xuexi_all_list.extend(xuexi_list)
        mypokeexplist = await get_auto_win_exp(pokefight_level, fight_poke_id, mypokelist, mypokelevellist, mypokeexplist, poke_count[fight_poke_id])
        # print(f"{CHARA_NAME[fight_poke_id][0]}:{poke_count[fight_poke_id]}")
        get_egg_num = math.ceil(int(poke_count[fight_poke_id]) * (WIN_EGG/100))
        poke_eggid = await get_pokemon_eggid(int(fight_poke_id))
        get_egg_list[poke_eggid] = get_egg_list.get(poke_eggid, 0) + get_egg_num
    
    for poke_eggid in get_egg_list:
        msg += f'获得了{CHARA_NAME[poke_eggid][0]}精灵蛋x{get_egg_list[poke_eggid]}\n'
        # print(f"{CHARA_NAME[poke_eggid][0]}:{get_egg_list[poke_eggid]}")
        await POKE._add_pokemon_egg(uid, poke_eggid, get_egg_list[poke_eggid])
    
    #获取学习机
    xuexi_num = math.ceil(pokefight_num * (WIN_PROP/100))
    if xuexi_num > 0:
        msg += "\n"
        xuexi_add_list = list(set(xuexi_all_list))
        sampled_data_xuexi= random.choices(xuexi_add_list, k=xuexi_num)
        sampled_xuexi_list = list(sampled_data_xuexi)
        xuexi_count = Counter(sampled_xuexi_list)
        msg += f'获得了招式学习机x{xuexi_num}\n(具体种类数量请自行查看背包)\n'
        for xuexi_name in xuexi_count:
            #print(f"{xuexi_name}:{xuexi_count[xuexi_name]}")
            await POKE._add_pokemon_technical(uid,xuexi_name,xuexi_count[xuexi_name])
    
    exp_mes = ''
    for pokeid in mypokelist:
        exp_mes += await add_exp(uid, pokeid, mypokeexplist[pokeid])
    if exp_mes:
        msg += f"\n经验结算{exp_mes}"
    await bot.send(msg, at_sender=True)

@sv_pokemon_tansuo.on_fullmatch(['野外探索'])
async def map_ts_test_noauto_use(bot, ev: Event):
    uid = ev.user_id
    last_send_time = time_send.get_user_time(uid)
    now_time = time.time()
    now_time = math.ceil(now_time)
    send_flag = 0
    if now_time - last_send_time <= TS_CD:
        return
    else:
        time_send.record_user_time(uid,now_time)
    if TS_PIC == 1:
        await get_ts_info_pic(bot, ev)
    else:
        await get_ts_info_wenzi(bot, ev)

async def get_ts_info_pic(bot, ev: Event):
    uid = ev.user_id
    mypokelist = await POKE._get_pokemon_list(uid)
    if mypokelist == 0:
        return await bot.send(
            '您还没有精灵，请输入 领取初始精灵+初始精灵名称 开局。\n初始精灵列表可输入[初始精灵列表]查询',
            at_sender=True,
        )
    mapinfo = await POKE._get_map_now(uid)
    if mapinfo[4] == 1:
        return await bot.send('您已经处于自动探索中了哦~', at_sender=True)
    this_map = mapinfo[1]
    if this_map == '':
        return await bot.send(
            '您还选择初始地区，请输入 选择初始地区+地区名称。', at_sender=True
        )
    my_team = await POKE.get_pokemon_group(uid)
    if my_team == '':
        return await bot.send(
            '您还没有创建队伍，请输入 创建队伍+宝可梦名称(中间用空格分隔)。',
            at_sender=True,
        )
    pokemon_team = my_team.split(',')
    mypokelist = []
    for bianhao in pokemon_team:
        bianhao = int(bianhao)
        mypokelist.append(bianhao)
    if didianlist[this_map]['type'] == '城镇' or didianlist[this_map]['type'] == '建筑':
        return await bot.send(
            '您当前所处的地点没有可探索的区域', at_sender=True
        )

    mapinfo = await POKE._get_map_now(uid)
    mychenghao, huizhang = await get_chenghao(uid)
    name = mapinfo[2]
    if name == uid:
        if ev.sender:
            sender = ev.sender
            if sender.get('nickname', '') != '':
                name = sender['nickname']
    mes = ''
    buttons = [
        Button('🏝️野外探索', '野外探索', '🏝️野外探索', action=1),
    ]
    name = str(name)[:10]
    bg_img = open_image(TEXT_PATH / 'duel_bg.jpg')
    vs_img = open_image(TEXT_PATH / 'vs.png').convert('RGBA').resize((100, 89))
    bg_img.paste(vs_img, (300, 12), vs_img)
    trainers_path = TEXT_PATH / 'trainers'
    if didianlist[this_map]['type'] == '野外':
        ts_z = TS_FIGHT + TS_PROP + TS_POKEMON
        ts_num = int(math.floor(random.uniform(0, ts_z)))
        ts_quality = TS_POKEMON
        if ts_num <= ts_quality:
            # 遇怪
            daliang_pokemon = await POKE.get_map_refresh(didianlist[this_map]['fname'],this_map)
            if int(daliang_pokemon) > 0:
                daling_num = int(math.floor(random.uniform(0, 100)))
                if daling_num <= DALIANG_POKE:
                    pokelist = []
                    pokelist.append(int(daliang_pokemon))
                else:
                    pokelist = didianlist[this_map]['pokemon']
            else:
                pokelist = didianlist[this_map]['pokemon']
            dipokelist = random.sample(pokelist, 1)
            pokename = CHARA_NAME[dipokelist[0]][0]
            pokemonid = dipokelist[0]
            qun_num = int(math.floor(random.uniform(0, 100)))
            if qun_num <= QUN_POKE:
                pokemon_num = int(math.floor(random.uniform(3, 6)))
                for item in range(0,pokemon_num):
                    dipokelist.append(pokemonid)
                mes += f'野生宝可梦{pokename}群出现了\n'
            else:
                pokemon_num = 1
                mes += f'野生宝可梦{pokename}出现了\n'
            my_image = (
                open_image(trainers_path / '0.png')
                .convert('RGBA')
                .resize((120, 120))
            )
            di_image = (
                open_image(CHAR_ICON_PATH / f'{pokename}.png')
                .convert('RGBA')
                .resize((120, 120))
            )
            bg_img.paste(my_image, (0, 0), my_image)
            bg_img.paste(di_image, (580, 0), di_image)
            img_draw = ImageDraw.Draw(bg_img)
            img_draw.text(
                (125, 30),
                mychenghao,
                black_color,
                sr_font_24,
                'lm',
            )
            img_draw.text(
                (125, 65),
                f'{name}',
                black_color,
                sr_font_24,
                'lm',
            )
            if pokemon_num > 1:
                img_draw.text(
                    (575, 30),
                    '野生宝可梦群',
                    black_color,
                    sr_font_24,
                    'rm',
                )
            else:
                img_draw.text(
                    (575, 30),
                    '野生宝可梦',
                    black_color,
                    sr_font_24,
                    'rm',
                )
            img_draw.text(
                (575, 65),
                f'{pokename}',
                black_color,
                sr_font_24,
                'rm',
            )
            (
                bg_img,
                bg_num,
                img_height,
                mes_list,
                mypokelist,
                dipokelist,
            ) = await fight_yw_ys_s(
                bg_img,
                bot,
                ev,
                uid,
                mypokelist,
                dipokelist,
                didianlist[this_map]['level'][0],
                didianlist[this_map]['level'][1],
                1,
            )
            if math.ceil((img_height + 120) / 1280) > bg_num:
                bg_num += 1
                bg_img = await change_bg_img(bg_img, bg_num)
            img_draw = ImageDraw.Draw(bg_img)
            mes += mes_list
            if len(mypokelist) == 0:
                mes += f'\n您被野生宝可梦{pokename}打败了，眼前一黑'
                # mes_list.append(MessageSegment.text(mes))
                # await bot.send(mes, at_sender=True)
                img_draw.text(
                    (575, img_height + 30),
                    f'您被{pokename}打败了，眼前一黑',
                    black_color,
                    sr_font_20,
                    'rm',
                )
                bg_img.paste(di_image, (580, img_height), di_image)
                img_height += 160
            if len(dipokelist) == 0:
                if pokemon_num > 1:
                    mes += f'\n您打败了{pokename}群'
                    img_draw.text(
                        (125, img_height + 30),
                        f'您打败了{pokename}群',
                        black_color,
                        sr_font_20,
                        'lm',
                    )
                else:
                    mes += f'\n您打败了{pokename}'
                    img_draw.text(
                        (125, img_height + 30),
                        f'您打败了{pokename}',
                        black_color,
                        sr_font_20,
                        'lm',
                    )
                if pokemonid == 22 and '火' in POKEMON_LIST[mypokelist[0]][7]:
                    chongsheng_num = await POKE.get_chongsheng_num(uid,250)
                    if chongsheng_num >= 6666:
                        await POKE._add_pokemon_egg(uid, 250, 1)
                        mes += f'\n您获得了{CHARA_NAME[250][0]}精灵蛋x1'
                        await POKE._new_chongsheng_num(uid,250)
                    else:
                        await POKE.update_chongsheng(uid,250,pokemon_num)
                egg_num = 0
                for item in range(0,pokemon_num):
                    zs_num = int(math.floor(random.uniform(0, 100)))
                    if zs_num <= WIN_EGG:
                        egg_num += 1
                if egg_num > 0:
                    eggid = await get_pokemon_eggid(pokemonid)
                    mes += f'\n您获得了{CHARA_NAME[eggid][0]}精灵蛋x{egg_num}'
                    await POKE._add_pokemon_egg(uid, eggid, egg_num)
                    img_draw.text(
                        (125, img_height + 65),
                        f'您获得了{CHARA_NAME[eggid][0]}精灵蛋',
                        black_color,
                        sr_font_20,
                        'lm',
                    )
                pp_num = int(math.floor(random.uniform(0, 100)))
                if pp_num <= WIN_PROP:
                    ppname = ''
                    xuexi_list = POKEMON_XUEXI[pokemonid]
                    if len(xuexi_list) > 0:
                        while ppname == '':
                            jineng_name = random.sample(xuexi_list, 1)[0]
                            if JINENG_LIST[jineng_name][6] != '':
                                ppname = jineng_name
                            else:
                                xuexi_list.remove(jineng_name)
                            if len(xuexi_list) == 0:
                                return
                    if ppname != '':
                        await POKE._add_pokemon_technical(uid,ppname,1)
                        mes += f'\n您获得了招式学习机[{ppname}]x1'
                        img_draw.text(
                            (125, img_height + 95),
                            f'您获得了招式学习机[{ppname}]x1',
                            black_color,
                            sr_font_20,
                            'lm',
                        )
                bg_img.paste(my_image, (0, img_height), my_image)
                # mes_list.append(MessageSegment.text(mes))
                # await bot.send(mes, at_sender=True)
                img_height += 130
            img_bg = Image.new('RGB', (700, img_height), (255, 255, 255))
            img_bg.paste(bg_img, (0, 0))
            img_bg = await convert_img(img_bg)
            await bot.send_option(img_bg, buttons)

        else:
            ts_quality += TS_FIGHT
            if ts_num <= ts_quality:
                # 对战
                chenghao = str(random.sample(Call_Name, 1)[0])
                xingming = str(random.sample(First_Name, 1)[0]) + str(
                    random.sample(Last_Name, 1)[0]
                )
                diname = chenghao + ' ' + xingming
                pokelist = didianlist[this_map]['pokemon']
                maxnum = min(5, int(didianlist[this_map]['need']) + 1)
                min_level = (
                    didianlist[this_map]['level'][0] / 2
                    + didianlist[this_map]['level'][0]
                )
                max_level = (
                    didianlist[this_map]['level'][0] / 2
                    + didianlist[this_map]['level'][1]
                )
                pokenum = int(math.floor(random.uniform(1, maxnum)))
                # pokenum = 3
                dipokelist = []
                mes += f'{diname}向您发起了对战\n'
                for item in range(pokenum):
                    dipokelist.append(random.sample(pokelist, 1)[0])

                my_image = (
                    open_image(trainers_path / '0.png')
                    .convert('RGBA')
                    .resize((120, 120))
                )
                di_image = (
                    open_image(trainers_path / f'{chenghao}.png')
                    .convert('RGBA')
                    .resize((120, 120))
                )
                bg_img.paste(my_image, (0, 0), my_image)
                bg_img.paste(di_image, (580, 0), di_image)
                img_draw = ImageDraw.Draw(bg_img)
                img_draw.text(
                    (125, 30),
                    mychenghao,
                    black_color,
                    sr_font_24,
                    'lm',
                )
                img_draw.text(
                    (125, 65),
                    f'{name}',
                    black_color,
                    sr_font_24,
                    'lm',
                )
                img_draw.text(
                    (575, 30),
                    chenghao,
                    black_color,
                    sr_font_24,
                    'rm',
                )
                img_draw.text(
                    (575, 65),
                    xingming,
                    black_color,
                    sr_font_24,
                    'rm',
                )
                (
                    bg_img,
                    bg_num,
                    img_height,
                    mes_list,
                    mypokelist,
                    dipokelist,
                ) = await fight_yw_ys_s(
                    bg_img,
                    bot,
                    ev,
                    uid,
                    mypokelist,
                    dipokelist,
                    min_level,
                    max_level,
                )
                mes += mes_list
                if math.ceil((img_height + 120) / 1280) > bg_num:
                    bg_num += 1
                    bg_img = await change_bg_img(bg_img, bg_num)
                img_draw = ImageDraw.Draw(bg_img)
                if len(mypokelist) == 0:
                    mes += f'\n您被{diname}打败了，眼前一黑'
                    # mes_list.append(MessageSegment.text(mes))
                    img_draw.text(
                        (575, img_height + 30),
                        f'您被{diname}打败了，眼前一黑',
                        black_color,
                        sr_font_20,
                        'rm',
                    )
                    bg_img.paste(di_image, (580, img_height), di_image)
                    img_height += 130
                    # await bot.send(mes, at_sender=True)
                if len(dipokelist) == 0:
                    mes += f'\n您打败了{diname}\n'
                    img_draw.text(
                        (125, img_height + 30),
                        f'您打败了{diname}',
                        black_color,
                        sr_font_20,
                        'lm',
                    )

                    get_score = (int(didianlist[this_map]['need']) + 1) * 200
                    await SCORE.update_score(uid, get_score)
                    mes += f'您获得了{get_score}金钱'
                    img_draw.text(
                        (125, img_height + 65),
                        f'您获得了{get_score}金钱',
                        black_color,
                        sr_font_20,
                        'lm',
                    )
                    bg_img.paste(my_image, (0, img_height), my_image)
                    # mes_list.append(MessageSegment.text(mes))
                    # await bot.send(mes, at_sender=True)
                    img_height += 130
                img_bg = Image.new('RGB', (700, img_height), (255, 255, 255))
                img_bg.paste(bg_img, (0, 0))
                img_bg = await convert_img(img_bg)
                await bot.send_option(img_bg, buttons)
            else:
                prop_name = random.sample(ts_prop_list, 1)[0]
                await POKE._add_pokemon_prop(uid, prop_name, 1)
                await bot.send_option(f'您获得了道具[{prop_name}]', buttons)


async def get_ts_info_wenzi(bot, ev: Event):
    uid = ev.user_id
    mypokelist = await POKE._get_pokemon_list(uid)
    if mypokelist == 0:
        return await bot.send(
            '您还没有精灵，请输入 领取初始精灵+初始精灵名称 开局。\n初始精灵列表可输入[初始精灵列表]查询',
            at_sender=True,
        )
    mapinfo = await POKE._get_map_now(uid)
    if mapinfo[4] == 1:
        return await bot.send('您已经处于自动探索中了哦~', at_sender=True)
    this_map = mapinfo[1]
    if this_map == '':
        return await bot.send(
            '您还选择初始地区，请输入 选择初始地区+地区名称。', at_sender=True
        )
    my_team = await POKE.get_pokemon_group(uid)
    if my_team == '':
        return await bot.send(
            '您还没有创建队伍，请输入 创建队伍+宝可梦名称(中间用空格分隔)。',
            at_sender=True,
        )
    pokemon_team = my_team.split(',')
    mypokelist = []
    for bianhao in pokemon_team:
        bianhao = int(bianhao)
        mypokelist.append(bianhao)
    if didianlist[this_map]['type'] == '城镇' or didianlist[this_map]['type'] == '建筑':
        return await bot.send(
            '您当前处于的地点没有可探索的区域', at_sender=True
        )

    mes = ''
    buttons = [
        Button('🏝️野外探索', '野外探索', '🏝️野外探索', action=1),
    ]
    if didianlist[this_map]['type'] == '野外':
        ts_z = TS_FIGHT + TS_PROP + TS_POKEMON
        ts_num = int(math.floor(random.uniform(0, ts_z)))
        ts_quality = TS_POKEMON
        if ts_num <= ts_quality:
            # 遇怪
            daliang_pokemon = await POKE.get_map_refresh(didianlist[this_map]['fname'],this_map)
            if int(daliang_pokemon) > 0:
                daling_num = int(math.floor(random.uniform(0, 100)))
                if daling_num <= DALIANG_POKE:
                    pokelist = []
                    pokelist.append(int(daliang_pokemon))
                else:
                    pokelist = didianlist[this_map]['pokemon']
            else:
                pokelist = didianlist[this_map]['pokemon']
            dipokelist = random.sample(pokelist, 1)
            pokename = CHARA_NAME[dipokelist[0]][0]
            pokemonid = dipokelist[0]
            qun_num = int(math.floor(random.uniform(0, 100)))
            if qun_num <= QUN_POKE:
                pokemon_num = int(math.floor(random.uniform(3, 6)))
                for item in range(0,pokemon_num):
                    dipokelist.append(pokemonid)
                mes += f'野生宝可梦{pokename}群出现了\n'
            else:
                pokemon_num = 1
                mes += f'野生宝可梦{pokename}出现了\n'

            mes_list, mypokelist, dipokelist = await fight_yw_ys(
                uid,
                mypokelist,
                dipokelist,
                didianlist[this_map]['level'][0],
                didianlist[this_map]['level'][1],
                1,
            )

            mes += mes_list
            if len(mypokelist) == 0:
                mes += f'\n您被野生宝可梦{pokename}打败了，眼前一黑'

            if len(dipokelist) == 0:
                if pokemon_num > 1:
                    mes += f'\n您打败了{pokename}群'
                else:
                    mes += f'\n您打败了{pokename}'
                egg_num = 0
                if pokemonid == 22 and '火' in POKEMON_LIST[mypokelist[0]][7]:
                    chongsheng_num = await POKE.get_chongsheng_num(uid,250)
                    if chongsheng_num >= 6666:
                        await POKE._add_pokemon_egg(uid, 250, 1)
                        mes += f'\n您获得了{CHARA_NAME[250][0]}精灵蛋x1'
                        await POKE._new_chongsheng_num(uid,250)
                    else:
                        await POKE.update_chongsheng(uid,250,pokemon_num)
                for item in range(0,pokemon_num):
                    zs_num = int(math.floor(random.uniform(0, 100)))
                    if zs_num <= WIN_EGG:
                        egg_num += 1
                if egg_num > 0:
                    eggid = await get_pokemon_eggid(pokemonid)
                    mes += f'\n您获得了{CHARA_NAME[eggid][0]}精灵蛋x{egg_num}'
                    await POKE._add_pokemon_egg(uid, eggid, egg_num)
                pp_num = int(math.floor(random.uniform(0, 100)))
                if pp_num <= WIN_PROP:
                    ppname = ''
                    xuexi_list = POKEMON_XUEXI[pokemonid]
                    if len(xuexi_list) > 0:
                        while ppname == '':
                            jineng_name = random.sample(xuexi_list, 1)[0]
                            if JINENG_LIST[jineng_name][6] != '':
                                ppname = jineng_name
                            else:
                                xuexi_list.remove(jineng_name)
                            if len(xuexi_list) == 0:
                                return
                    if ppname != '':
                        await POKE._add_pokemon_technical(uid,ppname,1)
                        mes += f'\n您获得了招式学习机[{ppname}]x1'
            await bot.send_option(mes, buttons)
            
        else:
            ts_quality += TS_FIGHT
            if ts_num <= ts_quality:
                # 对战
                chenghao = str(random.sample(Call_Name, 1)[0])
                xingming = str(random.sample(First_Name, 1)[0]) + str(
                    random.sample(Last_Name, 1)[0]
                )
                diname = chenghao + ' ' + xingming
                pokelist = didianlist[this_map]['pokemon']
                maxnum = min(5, int(didianlist[this_map]['need']) + 1)
                min_level = (
                    didianlist[this_map]['level'][0] / 2
                    + didianlist[this_map]['level'][0]
                )
                max_level = (
                    didianlist[this_map]['level'][0] / 2
                    + didianlist[this_map]['level'][1]
                )
                pokenum = int(math.floor(random.uniform(1, maxnum)))
                # pokenum = 3
                dipokelist = []
                mes += f'{diname}向您发起了对战\n'
                for item in range(pokenum):
                    dipokelist.append(random.sample(pokelist, 1)[0])

                mes_list, mypokelist, dipokelist = await fight_yw_ys(
                    uid, mypokelist, dipokelist, min_level, max_level
                )
                mes += mes_list
                if len(mypokelist) == 0:
                    mes += f'\n您被{diname}打败了，眼前一黑'
                if len(dipokelist) == 0:
                    mes += f'\n您打败了{diname}\n'

                    get_score = (int(didianlist[this_map]['need']) + 1) * 200
                    await SCORE.update_score(uid, get_score)
                    mes += f'您获得了{get_score}金钱'
                await bot.send_option(mes, buttons)
            else:
                prop_name = random.sample(ts_prop_list, 1)[0]
                await POKE._add_pokemon_prop(uid, prop_name, 1)
                await bot.send_option(f'您获得了道具[{prop_name}]', buttons)


@sv_pokemon_tansuo.on_fullmatch(['野外垂钓'])
async def map_ts_test_noauto_use_chuidiao(bot, ev: Event):
    uid = ev.user_id
    last_send_time = time_send.get_user_time(uid)
    now_time = time.time()
    now_time = math.ceil(now_time)
    send_flag = 0
    if now_time - last_send_time <= TS_CD:
        return
    time_send.record_user_time(uid,now_time)
    if TS_PIC == 1:
        await get_cd_info_pic(bot, ev)
    else:
        await get_cd_info_wenzi(bot, ev)
    
async def get_cd_info_pic(bot, ev: Event):
    uid = ev.user_id

    mypokelist = await POKE._get_pokemon_list(uid)
    if mypokelist == 0:
        return await bot.send(
            '您还没有精灵，请输入 领取初始精灵+初始精灵名称 开局。\n初始精灵列表可输入[初始精灵列表]查询',
            at_sender=True,
        )
    mapinfo = await POKE._get_map_now(uid)
    if mapinfo[4] == 1:
        return await bot.send('您已经处于自动探索中了哦~', at_sender=True)
    this_map = mapinfo[1]
    if this_map == '':
        return await bot.send(
            '您还选择初始地区，请输入 选择初始地区+地区名称。', at_sender=True
        )
    my_team = await POKE.get_pokemon_group(uid)
    if my_team == '':
        return await bot.send(
            '您还没有创建队伍，请输入 创建队伍+宝可梦名称(中间用空格分隔)。',
            at_sender=True,
        )
    pokemon_team = my_team.split(',')
    mypokelist = []
    for bianhao in pokemon_team:
        bianhao = int(bianhao)
        mypokelist.append(bianhao)
    if didianlist[this_map]['type'] == '城镇' or didianlist[this_map]['type'] == '建筑':
        return await bot.send(
            '您当前所处的地点没有可探索的区域', at_sender=True
        )

    mapinfo = await POKE._get_map_now(uid)
    mychenghao, huizhang = await get_chenghao(uid)
    name = mapinfo[2]
    if name == uid:
        if ev.sender:
            sender = ev.sender
            if sender.get('nickname', '') != '':
                name = sender['nickname']
    mes = ''
    buttons = [
        Button('🏝野外垂钓', '野外垂钓', '🏝野外垂钓', action=1),
    ]
    name = str(name)[:10]
    bg_img = open_image(TEXT_PATH / 'duel_bg.jpg')
    vs_img = open_image(TEXT_PATH / 'vs.png').convert('RGBA').resize((100, 89))
    bg_img.paste(vs_img, (300, 12), vs_img)
    trainers_path = TEXT_PATH / 'trainers'
    if didianlist[this_map]['type'] == '野外':
        # 遇怪
        if didianlist[this_map]['pokemon_s'] is not None:
            if huizhang >= 5:
                chuidiao_key = '5'
            elif huizhang >= 3:
                chuidiao_key = '3'
            elif huizhang >= 1:
                chuidiao_key = '1'
            else:
                return await bot.send(
                    '您还没有钓竿，请取得1枚以上徽章后再来尝试', at_sender=True
                )
            pokelist = didianlist[this_map]['pokemon_s'][chuidiao_key][
                'pokemon'
            ]
            dipokelist = random.sample(pokelist, 1)
            pokename = CHARA_NAME[dipokelist[0]][0]
            pokemonid = dipokelist[0]
            mes += f'野生宝可梦{pokename}出现了\n'
            my_image = (
                open_image(trainers_path / '0.png')
                .convert('RGBA')
                .resize((120, 120))
            )
            di_image = (
                open_image(CHAR_ICON_PATH / f'{pokename}.png')
                .convert('RGBA')
                .resize((120, 120))
            )
            bg_img.paste(my_image, (0, 0), my_image)
            bg_img.paste(di_image, (580, 0), di_image)
            img_draw = ImageDraw.Draw(bg_img)
            img_draw.text(
                (125, 30),
                mychenghao,
                black_color,
                sr_font_24,
                'lm',
            )
            img_draw.text(
                (125, 65),
                f'{name}',
                black_color,
                sr_font_24,
                'lm',
            )
            img_draw.text(
                (575, 30),
                '野生宝可梦',
                black_color,
                sr_font_24,
                'rm',
            )
            img_draw.text(
                (575, 65),
                f'{pokename}',
                black_color,
                sr_font_24,
                'rm',
            )
            (
                bg_img,
                bg_num,
                img_height,
                mes_list,
                mypokelist,
                dipokelist,
            ) = await fight_yw_ys_s(
                bg_img,
                bot,
                ev,
                uid,
                mypokelist,
                dipokelist,
                didianlist[this_map]['pokemon_s'][chuidiao_key]['level'][0],
                didianlist[this_map]['pokemon_s'][chuidiao_key]['level'][1],
                1,
            )
            if math.ceil((img_height + 120) / 1280) > bg_num:
                bg_num += 1
                bg_img = await change_bg_img(bg_img, bg_num)
            img_draw = ImageDraw.Draw(bg_img)
            mes += mes_list
            if len(mypokelist) == 0:
                mes += f'\n您被野生宝可梦{pokename}打败了，眼前一黑'
                # mes_list.append(MessageSegment.text(mes))
                # await bot.send(mes, at_sender=True)
                img_draw.text(
                    (575, img_height + 30),
                    f'您被{pokename}打败了，眼前一黑',
                    black_color,
                    sr_font_20,
                    'rm',
                )
                bg_img.paste(di_image, (580, img_height), di_image)
                img_height += 160
            if len(dipokelist) == 0:
                mes += f'\n您打败了{pokename}'
                # mes_list.append(MessageSegment.text(mes))
                # await bot.send(mes, at_sender=True)
                img_draw.text(
                    (125, img_height + 30),
                    f'您打败了{pokename}',
                    black_color,
                    sr_font_20,
                    'lm',
                )
                zs_num = int(math.floor(random.uniform(0, 100)))
                if zs_num <= WIN_EGG:
                    eggid = await get_pokemon_eggid(pokemonid)
                    print(pokemonid)
                    print(eggid)
                    mes += f'\n您获得了{CHARA_NAME[eggid][0]}精灵蛋'
                    await POKE._add_pokemon_egg(uid, eggid, 1)
                    img_draw.text(
                        (125, img_height + 65),
                        f'您获得了{CHARA_NAME[eggid][0]}精灵蛋',
                        black_color,
                        sr_font_20,
                        'lm',
                    )
                pp_num = int(math.floor(random.uniform(0, 100)))
                if pp_num <= WIN_PROP:
                    ppname = ''
                    xuexi_list = POKEMON_XUEXI[pokemonid]
                    if len(xuexi_list) > 0:
                        while ppname == '':
                            jineng_name = random.sample(xuexi_list, 1)[0]
                            if JINENG_LIST[jineng_name][6] != '':
                                ppname = jineng_name
                            else:
                                xuexi_list.remove(jineng_name)
                            if len(xuexi_list) == 0:
                                return
                    if ppname != '':
                        await POKE._add_pokemon_technical(uid,ppname,1)
                        mes += f'\n您获得了招式学习机[{ppname}]x1'
                        img_draw.text(
                            (125, img_height + 95),
                            f'您获得了招式学习机[{ppname}]x1',
                            black_color,
                            sr_font_20,
                            'lm',
                        )
                bg_img.paste(my_image, (0, img_height), my_image)
                # mes_list.append(MessageSegment.text(mes))
                # await bot.send(mes, at_sender=True)
                img_height += 160
            img_bg = Image.new('RGB', (700, img_height), (255, 255, 255))
            img_bg.paste(bg_img, (0, 0))
            img_bg = await convert_img(img_bg)
            await bot.send_option(img_bg, buttons)
        else:
            return await bot.send('当前地点无法垂钓', at_sender=True)

async def get_cd_info_wenzi(bot, ev: Event):
    uid = ev.user_id
    mypokelist = await POKE._get_pokemon_list(uid)
    if mypokelist == 0:
        return await bot.send(
            '您还没有精灵，请输入 领取初始精灵+初始精灵名称 开局。\n初始精灵列表可输入[初始精灵列表]查询',
            at_sender=True,
        )
    mapinfo = await POKE._get_map_now(uid)
    if mapinfo[4] == 1:
        return await bot.send('您已经处于自动探索中了哦~', at_sender=True)
    this_map = mapinfo[1]
    if this_map == '':
        return await bot.send(
            '您还选择初始地区，请输入 选择初始地区+地区名称。', at_sender=True
        )
    my_team = await POKE.get_pokemon_group(uid)
    if my_team == '':
        return await bot.send(
            '您还没有创建队伍，请输入 创建队伍+宝可梦名称(中间用空格分隔)。',
            at_sender=True,
        )
    pokemon_team = my_team.split(',')
    mypokelist = []
    for bianhao in pokemon_team:
        bianhao = int(bianhao)
        mypokelist.append(bianhao)
    if didianlist[this_map]['type'] == '城镇' or didianlist[this_map]['type'] == '建筑':
        return await bot.send(
            '您当前所处的地点没有可探索的区域', at_sender=True
        )
    buttons = [
        Button('🏝野外垂钓', '野外垂钓', '🏝野外垂钓', action=1),
    ]
    mychenghao, huizhang = await get_chenghao(uid)
    mes = ''
    if didianlist[this_map]['type'] == '野外':
        # 遇怪
        if didianlist[this_map]['pokemon_s'] is not None:
            if huizhang >= 5:
                chuidiao_key = '5'
            elif huizhang >= 3:
                chuidiao_key = '3'
            elif huizhang >= 1:
                chuidiao_key = '1'
            else:
                return await bot.send(
                    '您还没有钓竿，请取得1枚以上徽章后再来尝试', at_sender=True
                )
            pokelist = didianlist[this_map]['pokemon_s'][chuidiao_key][
                'pokemon'
            ]
            dipokelist = random.sample(pokelist, 1)
            pokename = CHARA_NAME[dipokelist[0]][0]
            pokemonid = dipokelist[0]
            mes += f'野生宝可梦{pokename}出现了\n'

            mes_list, mypokelist, dipokelist = await fight_yw_ys(
                uid,
                mypokelist,
                dipokelist,
                didianlist[this_map]['pokemon_s'][chuidiao_key]['level'][0],
                didianlist[this_map]['pokemon_s'][chuidiao_key]['level'][1],
                1,
            )
            mes += mes_list
            if len(mypokelist) == 0:
                mes += f'\n您被野生宝可梦{pokename}打败了，眼前一黑'

            if len(dipokelist) == 0:
                mes += f'\n您打败了{pokename}'

                zs_num = int(math.floor(random.uniform(0, 100)))
                if zs_num <= WIN_EGG:
                    eggid = await get_pokemon_eggid(pokemonid)
                    mes += f'\n您获得了{CHARA_NAME[eggid][0]}精灵蛋'
                    await POKE._add_pokemon_egg(uid, eggid, 1)
                pp_num = int(math.floor(random.uniform(0, 100)))
                if pp_num <= WIN_PROP:
                    ppname = ''
                    xuexi_list = POKEMON_XUEXI[pokemonid]
                    if len(xuexi_list) > 0:
                        while ppname == '':
                            jineng_name = random.sample(xuexi_list, 1)[0]
                            if JINENG_LIST[jineng_name][6] != '':
                                ppname = jineng_name
                            else:
                                xuexi_list.remove(jineng_name)
                            if len(xuexi_list) == 0:
                                return
                    if ppname != '':
                        await POKE._add_pokemon_technical(uid,ppname,1)
                        mes += f'\n您获得了招式学习机[{ppname}]x1'
            await bot.send_option(mes, buttons)
        else:
            return await bot.send('当前地点无法垂钓', at_sender=True)


@sv_pokemon_tansuo.on_prefix(('训练家对战', '训练家挑战', '挑战训练家'))
async def pokemon_pk_auto(bot, ev: Event):
    args = ev.text.split()
    if len(args) != 1:
        return await bot.send(
            '请输入 训练家对战+对战训练家昵称 中间用空格隔开。', at_sender=True
        )
    uid = ev.user_id
    last_send_time = time_send.get_user_time(uid)
    now_time = time.time()
    now_time = math.ceil(now_time)
    send_flag = 0
    if now_time - last_send_time <= TS_CD:
        return
    time_send.record_user_time(uid,now_time)
    mypokelist = await POKE._get_pokemon_list(uid)
    if mypokelist == 0:
        return await bot.send(
            '您还没有精灵，请输入 领取初始精灵+初始精灵名称 开局。\n初始精灵列表可输入[初始精灵列表]查询',
            at_sender=True,
        )
    mapinfo = await POKE._get_map_now(uid)
    if mapinfo[4] == 1:
        return await bot.send('自动探索中无法进行对战', at_sender=True)
    this_map = mapinfo[1]
    if this_map == '':
        return await bot.send(
            '您还选择初始地区，请输入 选择初始地区+地区名称。', at_sender=True
        )
    my_team = await POKE.get_pokemon_group(uid)
    if my_team == '':
        return await bot.send(
            '您还没有创建队伍，请输入 创建队伍+宝可梦名称(中间用空格分隔)。',
            at_sender=True,
        )
    pokemon_team = my_team.split(',')
    mypokelist = []
    for bianhao in pokemon_team:
        bianhao = int(bianhao)
        mypokelist.append(bianhao)

    mapinfo = await POKE._get_map_now(uid)
    name = mapinfo[2]
    if name == uid:
        if ev.sender:
            sender = ev.sender
            if sender.get('nickname', '') != '':
                name = sender['nickname']

    mychenghao, myhuizhang = await get_chenghao(uid)
    nickname = args[0]
    dimapinfo = await POKE._get_map_info_nickname(nickname)
    if dimapinfo[4] == 1:
        return await bot.send(f'{nickname}处于自动探索中，无法进行对战', at_sender=True)
    if dimapinfo[2] == 0:
        return await bot.send(
            '没有找到该训练家，请输入 正确的对战训练家昵称。', at_sender=True
        )

    diname = nickname
    if name == diname:
        return await bot.send('不能自己打自己哦。', at_sender=True)
    diuid = dimapinfo[2]
    dichenghao, dihuizhang = await get_chenghao(diuid)
    dipokelist = await POKE._get_pokemon_list(diuid)
    if mypokelist == 0:
        return await bot.send(
            f'{diname}还没有精灵，请输入 领取初始精灵+初始精灵名称 开局。\n初始精灵列表可输入[初始精灵列表]查询',
            at_sender=True,
        )
    di_team = await POKE.get_pokemon_group(diuid)
    if di_team == '':
        return await bot.send(
            f'{diname}您还没有创建队伍，请输入 创建队伍+宝可梦名称(中间用空格分隔)。',
            at_sender=True,
        )
    di_pokemon_team = di_team.split(',')
    dipokelist = []
    for bianhao in di_pokemon_team:
        bianhao = int(bianhao)
        dipokelist.append(bianhao)

    name = str(name)[:10]
    diname = str(diname)[:10]
    # 对战
    mes = ''
    bg_img = open_image(TEXT_PATH / 'duel_bg.jpg')
    vs_img = open_image(TEXT_PATH / 'vs.png').convert('RGBA').resize((100, 89))
    bg_img.paste(vs_img, (300, 12), vs_img)
    trainers_path = TEXT_PATH / 'trainers'
    my_image = (
        open_image(trainers_path / '0.png').convert('RGBA').resize((120, 120))
    )
    di_image = (
        open_image(trainers_path / '0.png').convert('RGBA').resize((120, 120))
    )
    mes += f"{mychenghao} {name} 向 {dichenghao} {diname} 发起了对战\n"
    bg_img.paste(my_image, (0, 0), my_image)
    bg_img.paste(di_image, (580, 0), di_image)
    img_draw = ImageDraw.Draw(bg_img)
    img_draw.text(
        (125, 30),
        mychenghao,
        black_color,
        sr_font_24,
        'lm',
    )
    img_draw.text(
        (125, 65),
        f'{name}',
        black_color,
        sr_font_24,
        'lm',
    )
    img_draw.text(
        (575, 30),
        dichenghao,
        black_color,
        sr_font_24,
        'rm',
    )
    img_draw.text(
        (575, 65),
        diname,
        black_color,
        sr_font_24,
        'rm',
    )
    (
        bg_img,
        bg_num,
        img_height,
        mes_list,
        mypokelist,
        dipokelist,
    ) = await fight_pk(
        bot, ev, bg_img, uid, diuid, mypokelist, dipokelist, name, diname
    )
    mes += mes_list
    if math.ceil((img_height + 120) / 1280) > bg_num:
        bg_num += 1
        bg_img = await change_bg_img(bg_img, bg_num)
    img_draw = ImageDraw.Draw(bg_img)
    if len(mypokelist) == 0:
        mes += f'\n您被{diname}打败了，眼前一黑'
        # mes_list.append(MessageSegment.text(mes))
        img_draw.text(
            (575, img_height + 30),
            f'{diname}打败了{name}',
            black_color,
            sr_font_20,
            'rm',
        )
        #
        # get_score = (int(mapinfo[0]) + 1) * 500
        # await SCORE.update_score(diuid, get_score)
        # mes += f'{diname}获得了{get_score}金钱'
        # img_draw.text(
        # (575, img_height + 65),
        # f'{diname}获得了{get_score}金钱',
        # black_color,
        # sr_font_20,
        # 'rm',
        # )
        bg_img.paste(di_image, (580, img_height), di_image)
        img_height += 130
        # await bot.send(mes, at_sender=True)
    if len(dipokelist) == 0:
        mes += f'\n您打败了{diname}\n'
        img_draw.text(
            (125, img_height + 30),
            f'{name}打败了{diname}',
            black_color,
            sr_font_20,
            'lm',
        )
        #
        # get_score = (int(dimapinfo[0]) + 1) * 500
        # await SCORE.update_score(uid, get_score)
        # mes += f'您获得了{get_score}金钱'
        # img_draw.text(
        # (125, img_height + 65),
        # f'{name}获得了{get_score}金钱',
        # black_color,
        # sr_font_20,
        # 'lm',
        # )
        bg_img.paste(my_image, (0, img_height), my_image)
        # mes_list.append(MessageSegment.text(mes))
        # await bot.send(mes, at_sender=True)
        img_height += 130
    img_bg = Image.new('RGB', (700, img_height), (255, 255, 255))
    img_bg.paste(bg_img, (0, 0))
    img_bg = await convert_img(img_bg)
    if TS_PIC == 1:
        await bot.send(img_bg)
    else:
        await bot.send(mes)


@sv_pokemon_map.on_prefix(['选择初始地区'])
async def pokemom_new_map(bot, ev: Event):
    args = ev.text.split()
    if len(args) < 1:
        return await bot.send('请输入 选择初始地区+地点名称。', at_sender=True)
    go_map = args[0]
    uid = ev.user_id

    mapinfo = await POKE._get_map_now(uid)
    this_map = mapinfo[1]
    my_hz = 0
    if this_map:
        return await bot.send(
            f'您已经处于{this_map}中，无法重选初始地区', at_sender=True
        )

    diqu_list = list(diqulist.keys())
    if go_map not in diqu_list:
        return await bot.send(
            f'地图上没有{go_map},请输入正确的地区名称', at_sender=True
        )
    if diqulist[go_map]['open'] == 1:
        go_didian = diqulist[go_map]['chushi']
        if ev.sender:
            sender = ev.sender
            name = sender['card'] or sender['nickname']
        else:
            name = uid
        await POKE._new_map_info(uid, go_didian, name)
        await bot.send(
            f"您已成功选择初始地区{diqulist[go_map]['name']}\n当前所在地{go_didian}\n可输入[当前地点信息]查询",
            at_sender=True,
        )
    else:
        return await bot.send(
            '当前地区暂未开放请先前往其他地区冒险', at_sender=True
        )


@sv_pokemon_map.on_fullmatch(['当前地点信息'])
async def map_info_now(bot, ev: Event):
    gid = ev.group_id
    uid = ev.user_id

    mapinfo = await POKE._get_map_now(uid)
    this_map = mapinfo[1]
    if this_map == '':
        return await bot.send(
            '您还没有开局，请输入 领取初始精灵+初始宝可梦名称。', at_sender=True
        )
    mes = ''
    buttons = []
    buttons.append(Button('前往', '前往', action=2))
    diquname = diqulist[didianlist[this_map]['fname']]['name']
    mes += f'当前所在地为:{diquname}-{this_map}\n'
    if didianlist[this_map]['type'] == '城镇':
        get_score = (int(mapinfo[0]) + 1) * 5000
        mychenghao, huizhang = await get_chenghao(uid)
        buttons.append(Button('打工', '打工', '打工', action=1))
        mes += f'根据您当前的训练家等级-{mychenghao}\n您打工可获得{get_score}金币\n'
    if didianlist[this_map]['type'] == '建筑':
        buttons.append(Button('首领信息', '首领信息', '首领信息', action=1))
        buttons.append(Button('首领挑战', '首领挑战', '首领挑战', action=1))
        mes += f"{didianlist[this_map]['content']}\n"
    if didianlist[this_map]['type'] == '野外':
        buttons.append(Button('🏝野外探索', '野外探索', '🏝野外探索', action=1))
        name_str = get_pokemon_name_list(didianlist[this_map]['pokemon'])
        mes += f'当前所在地野外探索遭遇的精灵为\n{name_str}\n'
        mes += f"等级:{didianlist[this_map]['level'][0]}-{didianlist[this_map]['level'][1]}\n"
        if didianlist[this_map]['pokemon_s']:
            buttons.append(Button('🏝野外垂钓', '野外垂钓', '🏝野外垂钓', action=1))
            pokemon_s_list = didianlist[this_map]['pokemon_s']
            mes += '当前所在地野外垂钓遭遇的精灵为\n'
            for item in pokemon_s_list:
                mes += f'拥有徽章数大于{item!s}枚时\n'
                name_str = get_pokemon_name_list(
                    pokemon_s_list[item]['pokemon']
                )
                mes += f'{name_str}\n'
                mes += f"等级:{pokemon_s_list[item]['level'][0]}-{pokemon_s_list[item]['level'][1]}\n"
    await bot.send_option(mes, buttons)


@sv_pokemon_map.on_command(['查看地图'])
async def show_map_info_now(bot, ev: Event):
    args = ev.text.split()
    if len(args) < 1:
        uid = ev.user_id

        mapinfo = await POKE._get_map_now(uid)
        this_map = mapinfo[1]
        if this_map == '':
            return await bot.send(
                '您还没有开局，请输入 领取初始精灵+初始宝可梦名称。', at_sender=True
            )
        diquname = didianlist[this_map]['fname']
    else:
        diquname = args[0]
        list_dizhi = list(diqulist.keys())
        if diquname not in list_dizhi:
            return await bot.send(
                f'地图上没有{diquname},请输入正确的地区名称', at_sender=True
            )
        if diqulist[diquname]['open'] == 0:
            return await bot.send(
                '当前地区暂未开放请先前往其他地区冒险', at_sender=True
            )
    buttonlist = []
    buttonlist.append('前往')
    mes = f'{diquname}地点：'
    for didianname in didianlist:
        didianinfo = didianlist[didianname]
        if didianinfo['fname'] == diquname:
            # mes += f"\n[{didianname}] (mqqapi://aio/inlinecmd?command=前往{didianname}&reply=false&enter=true)"
            mes += f"\n{didianname}"
            if didianinfo['type'] == '城镇':
                mes += f" {didianinfo['type']}"
                if int(didianinfo['need']) >= 10:
                    mes += f" 成为冠军后"
                else:
                    mes += f" 需求徽章{didianinfo['need']}"
            elif didianinfo['type'] == '建筑':
                mes += f" {didianinfo['type']}"
                if int(didianinfo['need']) >= 10:
                    mes += f" 成为冠军后"
                else:
                    mes += f" 需求徽章{didianinfo['need']}"
                mes += f"\n{didianinfo['content']}"
            else:
                mes += f" Lv.{didianinfo['level'][0]}~{didianinfo['level'][1]}"
                if int(didianinfo['need']) >= 10:
                    mes += f" 成为冠军后"
                else:
                    mes += f" 需求徽章{didianinfo['need']}"
    buttons = [
        Button('前往', '前往', '前往', action=2),
    ]
    await bot.send_option(mes, buttons)

@sv_pokemon_map.on_command(('分布查询','精灵分布'))
async def pokemom_map_info_have(bot, ev: Event):
    args = ev.text.split()
    if len(args) < 1:
        return await bot.send('请输入 需要查询分宝可梦名称。', at_sender=True)
    pokename = args[0]
    bianhao = await get_poke_bianhao(pokename)
    if bianhao == 0:
        return await bot.send('请输入正确的宝可梦名称。', at_sender=True)
    mes = ''
    for didianname in didianlist:
        didianinfo = didianlist[didianname]
        if didianinfo['type'] == '野外':
            if bianhao in didianinfo['pokemon']:
                # mes += f"\n[{didianinfo['fname']}-{didianname}] (mqqapi://aio/inlinecmd?command=前往{didianname}&reply=false&enter=true)"
                mes += f"\n{didianinfo['fname']}-{didianname}"
                if int(didianinfo['need']) >= 10:
                    mes += f" 成为冠军后"
                else:
                    mes += f" 需求徽章{didianinfo['need']}"
            if didianinfo['pokemon_s']:
                pokemon_s_list = didianinfo['pokemon_s']
                chuidiao_flag = 0
                for item in pokemon_s_list:
                    if bianhao in pokemon_s_list[item]['pokemon']:
                        chuidiao_flag = 1
                if chuidiao_flag == 1:
                    mes += f"\n{didianinfo['fname']}-{didianname}【垂钓】"
                    if int(didianinfo['need']) >= 10:
                        mes += f" 成为冠军后"
                    else:
                        mes += f" 需求徽章{didianinfo['need']}"
    if mes == '':
        mes = f'{pokename}当前暂无获取途径'
    else:
        mes = f'{pokename}的获取途径为:{mes}'
    buttons = [
        Button('前往', '前往', '前往', action=2),
    ]
    await bot.send_option(mes, buttons)
    
    
@sv_pokemon_map.on_prefix(['前往'])
async def pokemom_go_map(bot, ev: Event):
    args = ev.text.split()
    if len(args) < 1:
        return await bot.send('请输入 前往+地点名称。', at_sender=True)
    go_map = args[0]
    uid = ev.user_id

    mapinfo = await POKE._get_map_now(uid)
    if mapinfo[4] == 1:
        return await bot.send('自动探索中，无法切换地图，请结束自动探索后再更换吧', at_sender=True)
    this_map = mapinfo[1]
    if this_map == '':
        return await bot.send(
            '您还没有开局，请输入 领取初始精灵+初始宝可梦名称。', at_sender=True
        )
    my_hz = mapinfo[0]
    buttons = [
        Button('当前地点信息', '当前地点信息', action=1),
    ]
    if go_map == this_map:
        return await bot.send(
            f'您已经处于{this_map}中，无需前往', at_sender=True
        )
    list_dizhi = list(didianlist.keys())
    if go_map not in list_dizhi:
        return await bot.send(
            f'地图上没有{go_map},请输入正确的地址名称', at_sender=True
        )
    if didianlist[go_map]['fname'] == didianlist[this_map]['fname']:
        if int(my_hz) >= int(didianlist[go_map]['need']):
            await POKE._add_map_now(uid, go_map)
            mes = f'您已到达{go_map},当前地址信息可点击下方按钮查询'
            await bot.send_option(mes, buttons)
        else:
            if int(didianlist[go_map]['need']) >= 10:
                mes = f"需要成为冠军后才能前往{go_map},您当前无法前往"
            else:
                mes = f"前往{go_map}所需徽章为{didianlist[go_map]['need']}枚,您的徽章为{my_hz}枚,无法前往"
            return await bot.send(mes,at_sender=True)
    else:
        if int(my_hz) >= 8:
            await POKE._add_map_now(uid, go_map)
            mes = f'您已到达{go_map},当前地址信息可点击下方按钮查询'
            await bot.send_option(mes, buttons)
        else:
            return await bot.send(
                f'跨地区前往需要8枚徽章,您的徽章为{my_hz!s}枚,无法前往',
                at_sender=True,
            )

@sv_pm_config.on_fullmatch(['刷新每日大量出现'])
async def new_pokemom_show(bot, ev: Event):
    didianlistkey = {}
    for diqu in diqulist:
        if diqulist[diqu]['open'] == 1:
            didianlistkey[diqu] = []
    for didian in didianlist:
        if didianlist[didian]['type'] == '野外':
            didianlistkey[didianlist[didian]['fname']].append(didian)
    mes = '野生宝可梦大量出现了'
    chara_id_list = list(CHARA_NAME.keys())
    for jinyongid in jinyonglist:
        chara_id_list.remove(jinyongid)
    for diqu in diqulist:
        if diqulist[diqu]['open'] == 1:
            didianname = random.sample(didianlistkey[diqu], 1)[0]
            sj_num = int(math.floor(random.uniform(0, 100)))
            if sj_num <= 15:
                zx_min = 0
                zx_max = 300
            elif sj_num <= 45:
                zx_min = 280
                zx_max = 400
            elif sj_num <= 75:
                zx_min = 380
                zx_max = 500
            elif sj_num <= 95:
                zx_min = 480
                zx_max = 550
            else:
                zx_min = 520
                zx_max = 999
            
            find_flag = 0
            while find_flag == 0:
                random.shuffle(chara_id_list)
                pokeminid = chara_id_list[0]
                pokemon_zz = int(POKEMON_LIST[pokeminid][1]) + int(POKEMON_LIST[pokeminid][2]) + int(POKEMON_LIST[pokeminid][3]) + int(POKEMON_LIST[pokeminid][4]) + int(POKEMON_LIST[pokeminid][5]) + int(POKEMON_LIST[pokeminid][6])
                if pokemon_zz <= zx_max and pokemon_zz >= zx_min:
                    await POKE.update_map_refresh(diqu,didianname,pokeminid)
                    mes += f"\n{diqu}地区-{didianname} 出现了大量的 {CHARA_NAME[pokeminid][0]}"
                    find_flag = 1
    buttons = [
        Button('前往', '前往', action=2),
    ]
    await bot.send_option(mes, buttons)

@sv_pm_config.on_command(['发放奖励'])
async def give_prop_pokemon_info(bot, ev: Event):
    args = ev.text.split()
    if len(args) < 2:
        return await bot.send('请输入 发放奖励[道具/精灵蛋][名称][数量]。', at_sender=True)
    proptype = args[0]
    if proptype not in ['金币','金钱','道具','精灵蛋','宝可梦蛋','蛋','学习机']:
        return await bot.send('请输入正确的类型 道具/精灵蛋/学习机。', at_sender=True)
    if ev.at is not None:
        suid = ev.at
        smapinfo = await POKE._get_map_now(suid)
        if smapinfo[2] == 0:
            return await bot.send(
                '没有找到该训练家，请at需要发放奖励的对象/该人员未成为训练家。',
                at_sender=True,
            )
        sname = smapinfo[2]
    else:
        if proptype in ['金币','金钱']:
            if len(args) < 3:
                return await bot.send('请输入正确的指令 发放奖励[金币/金钱][数量][昵称/at]。', at_sender=True)
            snickname = args[2]
        else:
            if len(args) < 4:
                return await bot.send('请输入正确的指令 发放奖励[道具/精灵蛋/学习机][名称][数量][昵称/at]。',at_sender=True)
            snickname = args[3]
        smapinfo = await POKE._get_map_info_nickname(snickname)
        if smapinfo[2] == 0:
            return await bot.send('没有找到该训练家，请输入 正确的训练家昵称或at该名训练家。',at_sender=True)
        suid = smapinfo[2]
        sname = snickname
    propname = args[1]
    if len(args) >= 3 and proptype in ['道具', '精灵蛋', '宝可梦蛋', '蛋', '学习机']:
        propnum = int(args[2])
    else:
        propnum = 1
    if proptype == '金币' or proptype == '金钱':
        propnum = int(args[1])
        await SCORE.update_score(suid, propnum)
        mes = f'奖励发放成功！{sname} 获得了金币x{propnum}。'
    if proptype == '道具':
        propkeylist = proplist.keys()
        if propname not in propkeylist:
            return await bot.send('无法找到该道具，请输入正确的道具名称。', at_sender=True)
        await POKE._add_pokemon_prop(suid, propname, propnum)
        mes = f'奖励发放成功！{sname} 获得了道具{propname}x{propnum}。'
    if proptype == '精灵蛋' or proptype == '宝可梦蛋' or proptype == '蛋':
        proptype = '精灵蛋'
        bianhao = await get_poke_bianhao(propname)
        if bianhao == 0:
            return await bot.send('请输入正确的宝可梦名称。', at_sender=True)
        await POKE._add_pokemon_egg(suid, bianhao, propnum)
        mes = f'奖励发放成功！{sname} 获得了 {propname}精灵蛋x{propnum}。'
    if proptype == '学习机':
        jinenglist = JINENG_LIST.keys()
        if propname not in jinenglist:
            return await bot.send('无法找到该技能，请输入正确的技能学习机名称。', at_sender=True)
        await POKE._add_pokemon_technical(suid,propname,propnum)
        mes = f'奖励发放成功！{sname}获得了{propname}学习机x{propnum}。'
    await bot.send(mes)

@sv_pm_config.on_command(['全体发放奖励'])
async def give_prop_pokemon_info_all(bot, ev: Event):
    args = ev.text.split()
    if len(args) < 2:
        return await bot.send('请输入 全体发放奖励[道具/精灵蛋/金币][名称][数量]。', at_sender=True)
    proptype = args[0]
    if proptype not in ['金币','金钱','道具','精灵蛋','宝可梦蛋','蛋']:
        return await bot.send('请输入正确的类型 道具/精灵蛋/金币。', at_sender=True)
    propname = args[1]
    if len(args) == 3:
        propnum = int(args[2])
    else:
        propnum = 1
    if propnum < 1:
        return await bot.send('赠送物品的数量需大于1。', at_sender=True)
    game_user_list = await POKE.get_game_user_list()
    game_user_num = len(game_user_list)
    if proptype == '金币' or proptype == '金钱':
        propnum = int(args[1])
        for uid in game_user_list:
            await SCORE.update_score(uid[0], propnum)
        mes = f'奖励发放成功！总计{game_user_num}名玩家(徽章1枚及以上)，获得了金币x{propnum}。'
    if proptype == '道具':
        propkeylist = proplist.keys()
        if propname not in propkeylist:
            return await bot.send('无法找到该道具，请输入正确的道具名称。', at_sender=True)
        for uid in game_user_list:
            await POKE._add_pokemon_prop(uid[0], propname, propnum)
        mes = f'奖励发放成功！总计{game_user_num}名玩家(徽章1枚及以上)，获得了道具{propname}x{propnum}。'
    if proptype == '精灵蛋' or proptype == '宝可梦蛋' or proptype == '蛋':
        proptype = '精灵蛋'
        bianhao = await get_poke_bianhao(propname)
        if bianhao == 0:
            return await bot.send('请输入正确的宝可梦名称。', at_sender=True)
        for uid in game_user_list:
            await POKE._add_pokemon_egg(uid[0], bianhao, propnum)
        mes = f'奖励发放成功！总计{game_user_num}名玩家(徽章1枚及以上)，获得了 {propname}精灵蛋x{propnum}。'
    await bot.send(mes)

@sv_pm_config.on_command(['发放精灵'])
async def give_pokemon_gm(bot, ev: Event):
    args = ev.text.split()
    snickname = args[0]
    smapinfo = await POKE._get_map_info_nickname(snickname)
    if smapinfo[2] == 0:
        return await bot.send('没有找到该训练家，请输入 正确的训练家昵称或at该名训练家。',at_sender=True)
    suid = smapinfo[2]
    sname = snickname
    propname = args[1]
    bianhao = await get_poke_bianhao(propname)
    if bianhao == 0:
        return await bot.send('请输入正确的宝可梦名称。', at_sender=True)
    pokemon_info = []
    pokemon_info.append(args[2])
    pokemon_info.append(args[3])
    pokemon_info.append(args[4])
    pokemon_info.append(args[5])
    pokemon_info.append(args[6])
    pokemon_info.append(args[7])
    pokemon_info.append(args[8])
    pokemon_info.append(args[9])
    pokemon_info.append(args[10])
    pokemon_info.append(args[11])
    pokemon_info.append(args[12])
    pokemon_info.append(args[13])
    pokemon_info.append(args[14])
    pokemon_info.append(args[15])
    pokemon_info.append(args[16])
    pokemon_info.append(0)
    pokemon_info.append(args[17])
    await POKE._add_pokemon_info(suid, bianhao, pokemon_info)
    mes = f"精灵发放成功，{sname}获得了{propname} Lv.{args[2]}"
    await bot.send(mes)

@sv_pm_config.on_command(['数据转移'])
async def update_pokemon_info(bot, ev: Event):
    args = ev.text.split()
    if len(args) < 2:
        return await bot.send('请输入 数据转移 [新平台的用户ID][老平台的用户ID]。', at_sender=True)
    newuid = args[0]
    olduid = args[1]
    await chongkai(newuid)
    await POKE._change_poke_info(newuid,olduid)
    await POKE.change_pokemon_egg(newuid,olduid)
    await POKE.change_pokemon_map(newuid,olduid)
    await POKE.change_pokemon_group(newuid,olduid)
    await POKE._change_poke_star(newuid,olduid)
    await POKE.change_pokemon_prop(newuid,olduid)
    await POKE.change_exchange_uid(newuid,olduid)
    await POKE.change_technical_uid(newuid,olduid)
    await POKE._change_poke_starrush_uid(newuid,olduid)
    await SCORE.change_score(newuid,olduid)
    await bot.send('用户数据转移成功')
    
@sv_pm_config.on_command(('查看状态', '状态查看'))
async def get_my_poke_info_sv(bot, ev: Event):
    args = ev.text.split()
    if len(args) < 1:
        return await bot.send('请输入 精灵状态+宝可梦名称 中间用空格隔开。', at_sender=True)
    pokename = args[0]
    uid = ev.user_id
    if ev.at is not None:
        uid = ev.at
    else:
        nickname = args[1]
        mapinfo = await POKE._get_map_info_nickname(nickname)
        if mapinfo[2] == 0:
            return await bot.send(
                '没有找到该训练家，请输入 正确的训练家昵称或at该名训练家。',
                at_sender=True,
            )
        uid = mapinfo[2]
    bianhao = await get_poke_bianhao(pokename)
    if bianhao == 0:
        return await bot.send('请输入正确的宝可梦名称。', at_sender=True)
    pokemon_info = await get_pokeon_info(uid, bianhao)
    if pokemon_info == 0:
        return await bot.send(
            f'当前用户还没有{CHARA_NAME[bianhao][0]}。', at_sender=True
        )
    im, jinhualist = await draw_pokemon_info(uid, pokemon_info, bianhao)
    await bot.send(im)

@sv_pokemon_map.on_fullmatch(['标记消息推送'])
async def new_refresh_send_group(bot, ev: Event):
    groupid = ev.group_id
    botid = ev.bot_id
    if groupid is None:
        groupid = ev.user_id
    await POKE.update_refresh_send(groupid,botid)
    await bot.send('消息推送房间/群标记成功',at_sender=True)
    
@sv_pokemon_map.on_fullmatch(['清除消息推送'])
async def del_refresh_send_group(bot, ev: Event):
    groupid = ev.group_id
    botid = ev.bot_id
    await POKE.delete_refresh_send(groupid)
    await bot.send('消息推送房间/群清除成功',at_sender=True)

@sv_pokemon_map.on_fullmatch(['大量出现信息推送'])
async def get_day_pokemon_refresh_send(bot, ev: Event):
    refresh_list = await POKE.get_map_refresh_list()
    mes = "野生宝可梦大量出现了"
    for refresh in refresh_list:
        mes += f'\n{POKEMON_LIST[int(refresh[2])][0]} 在 {refresh[0]}地区-{refresh[1]} 大量出现了'
    mes += '\n可以输入[标记消息推送]每次刷新会自动推送宝可梦大量出现信息'
    refresh_send_list = await POKE.get_refresh_send_list()
    for refresh in refresh_send_list:
        try:
            for bot_id in gss.active_bot:
                await gss.active_bot[bot_id].target_send(
                    mes,
                    'group',
                    refresh[0],
                    refresh[1],
                    '',
                    '',
                )
        except Exception as e:
            logger.warning(f'[每日大量出现推送]群 14559-188477 推送失败!错误信息:{e}')

@scheduler.scheduled_job('cron', day_of_week ='6', hour='23', minute='59',second='0')
async def pokemon_every_week():
    pipeilist = await POKE.get_map_pipei_list()
    now = datetime.now(pytz.timezone('Asia/Shanghai'))
    nowday = now.day
    monthflag = 0
    if now.day <= 7: #每月1号结算
        monthflag = 1
    for detail in pipeilist:
        diduanwei = await get_now_duanwei(detail[1])
        if diduanwei == '新手级':
            add_score = 1000000
            new_pipei_num = 0
            if monthflag == 1:
                add_score = 11000000
                new_pipei_num = 0
        elif diduanwei == '精灵球级':
            add_score = 2000000
            new_pipei_num = 0
            if monthflag == 1:
                add_score = 22000000
                new_pipei_num = 0
                await POKE._add_pokemon_prop(detail[0], '银色王冠', 1)
        elif diduanwei == '超级球级':
            add_score = 3000000
            new_pipei_num = 200
            if monthflag == 1:
                add_score = 33000000
                new_pipei_num = 0
                await POKE._add_pokemon_prop(detail[0], '银色王冠', 2)
        elif diduanwei == '高级球级':
            add_score = 4000000
            new_pipei_num = 400
            if monthflag == 1:
                add_score = 44000000
                new_pipei_num = 0
                await POKE._add_pokemon_prop(detail[0], '金色王冠', 1)
                await POKE._add_pokemon_prop(detail[0], '银色王冠', 1)
        elif diduanwei == '大师球级':
            add_score = 5000000
            new_pipei_num = 600
            if monthflag == 1:
                add_score = 55000000
                new_pipei_num = 0
                await POKE._add_pokemon_prop(detail[0], '金色王冠', 2)
                await POKE._add_pokemon_prop(detail[0], '银色王冠', 2)
        await SCORE.update_score(detail[0], add_score)
        await POKE.update_map_pipei(detail[0], new_pipei_num)
        
# 每日定点执行每日大量出现精灵刷新
@scheduler.scheduled_job('cron', hour ='*')
async def refresh_pokemon_day():
    now = datetime.now(pytz.timezone('Asia/Shanghai'))
    if now.hour not in [4,12,20]:
        return
    didianlistkey = {}
    for diqu in diqulist:
        if diqulist[diqu]['open'] == 1:
            didianlistkey[diqu] = []
    for didian in didianlist:
        if didianlist[didian]['type'] == '野外':
            didianlistkey[didianlist[didian]['fname']].append(didian)
    mes = '野生宝可梦大量出现了'
    chara_id_list = list(CHARA_NAME.keys())
    for jinyongid in jinyonglist:
        chara_id_list.remove(jinyongid)
    for diqu in diqulist:
        if diqulist[diqu]['open'] == 1:
            didianname = random.sample(didianlistkey[diqu], 1)[0]
            sj_num = int(math.floor(random.uniform(0, 100)))
            if sj_num <= 15:
                zx_min = 0
                zx_max = 300
            elif sj_num <= 45:
                zx_min = 280
                zx_max = 400
            elif sj_num <= 75:
                zx_min = 380
                zx_max = 500
            elif sj_num <= 95:
                zx_min = 480
                zx_max = 550
            else:
                zx_min = 520
                zx_max = 999
            find_flag = 0
            
            while find_flag == 0:
                random.shuffle(chara_id_list)
                pokeminid = chara_id_list[0]
                pokemon_zz = int(POKEMON_LIST[pokeminid][1]) + int(POKEMON_LIST[pokeminid][2]) + int(POKEMON_LIST[pokeminid][3]) + int(POKEMON_LIST[pokeminid][4]) + int(POKEMON_LIST[pokeminid][5]) + int(POKEMON_LIST[pokeminid][6])
                if pokemon_zz <= zx_max and pokemon_zz >= zx_min:
                    await POKE.update_map_refresh(diqu,didianname,pokeminid)
                    mes += f"\n{diqu}地区-{didianname} 出现了大量的 {CHARA_NAME[pokeminid][0]}"
                    find_flag = 1
    refresh_send_list = await POKE.get_refresh_send_list()
    if refresh_send_list != 0:
        for refresh in refresh_send_list:
            try:
                for bot_id in gss.active_bot:
                    await gss.active_bot[bot_id].target_send(
                        mes,
                        'group',
                        refresh[0],
                        refresh[1],
                        '',
                        '',
                    )
            except Exception as e:
                print(f'[每日大量出现推送]群 {refresh[0]} 推送失败!错误信息:{e}')
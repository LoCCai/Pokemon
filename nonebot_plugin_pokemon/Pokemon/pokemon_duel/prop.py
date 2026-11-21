import math
from nonebot_plugin_pokemon.compat.sv import SV
from nonebot_plugin_pokemon.compat.models import Event
from nonebot_plugin_pokemon.compat.message_models import Button
import json
import pytz
import time
from .pokeconfg import *
from collections import Counter
from .until import *
from pathlib import Path
from datetime import datetime
from nonebot_plugin_pokemon.compat.gss import gss
from nonebot_plugin_pokemon.compat.logger import logger
from nonebot_plugin_pokemon.compat.aps import scheduler
from ..utils.dbbase.ScoreCounter import SCORE_DB

Excel_path = Path(__file__).parent
with Path.open(Excel_path / 'prop.json', encoding='utf-8') as f:
    prop_dict = json.load(f)
    proplist = prop_dict['proplist']
    bossproplist = prop_dict['bossproplist']
    propgachalist = prop_dict['gachalist']

TEXT_PATH = Path(__file__).parent / 'texture2D'

sv_pokemon_prop = SV('宝可梦道具', priority=5)
sv_pokemon_prop_sp = SV('宝可梦道具管理', pm=0)

class PM_HONGBAO:
    def __init__(self):
        self.hb_score = {}
        self.hb_use_score = {}
        self.hb_num = {}
        self.hb_use_num = {}
        self.hb_open_user = {}

    def insert_hongbao(self, kouling, score, num):
        self.hb_score[kouling] = score
        self.hb_num[kouling] = num
        self.hb_open_user[kouling] = []

    def open_hongbao(self, kouling, use_score, openuser):
        self.hb_use_score[kouling] = self.hb_use_score.get(kouling, 0) + use_score
        self.hb_use_num[kouling] = self.hb_use_num.get(kouling, 0) + 1
        self.hb_open_user[kouling].append(openuser)
    
    def get_hongbao(self, kouling):
        score = self.hb_score[kouling] if self.hb_score.get(kouling) is not None else 0
        use_score = self.hb_use_score[kouling] if self.hb_use_score.get(kouling) is not None else 0
        num = self.hb_num[kouling] if self.hb_num.get(kouling) is not None else 0
        use_num = self.hb_use_num[kouling] if self.hb_use_num.get(kouling) is not None else 0
        openuser = self.hb_open_user[kouling] if self.hb_open_user.get(kouling) is not None else []
        return score,use_score,num,use_num,openuser
    
    def hongbao_off(self, kouling):
        self.hb_score[kouling] = 0
        self.hb_use_score[kouling] = 0
        self.hb_use_num[kouling] = 0
        self.hb_num[kouling] = 0
        self.hb_open_user[kouling] = []
    
pmhongbao = PM_HONGBAO()

@sv_pokemon_prop.on_fullmatch(['道具帮助', '宝可梦道具帮助'])
async def pokemon_help_prop(bot, ev: Event):
    msg = """
             宝可梦道具帮助
指令：
1、道具商店(查看商城出售的道具)
2、首领商店(周本boss币相关商店)
3、道具信息【道具名】(查看道具的具体信息)
4、购买道具【道具名】【数量】(购买道具,数量默认为1)
5、兑换道具【道具名】【数量】(兑换首领商店道具,数量默认为1)
6、使用道具【道具名】【精灵名】【数量】(对宝可梦使用道具,数量默认为1)
7、携带道具【道具名】【精灵名】(让精灵携带道具)
8、取下道具【精灵名】(取下精灵的携带道具)
9、抽取道具【数量】（进行道具扭蛋，概率获得专属Z纯晶）
10、我的道具(查看我的道具列表)
11、我的学习机(查看我的招式学习机列表)
12、查看交易所(【类型】【名称】)(查看交易所寄售的商品，类型名称可为空)
13、交易所上架【类型】【名称】【数量】【单价】(上架物品到交易所，例：交易所上架 精灵蛋 皮丘 5 8888)
14、交易所购买【商品ID】【数量】(交易所购买商品，数量默认为1)
15、我的寄售(查看我寄售在交易所的商品)
16、赠送物品【类型】【名称】【数量】【赠送对象昵称】(给予xxx对象物品道具/精灵蛋，数量默认为1)
17、回收道具【道具名】【数量】(商店出售道具,数量默认为1)
注：
交易所寄售的商品出售成功会收取10%的手续费
PS
商店重磅推出随机精灵蛋业务，只要花费10万即可【购买随机精灵蛋】
上到神兽精灵蛋，下到御三家精灵蛋，应有尽有
现开放春季大酬宾，究极异兽已加入蛋池
每人每天限购50颗随机精灵蛋，先到先得哦~
 """
    buttons = [
        Button('💰道具商店', '道具商店', '💰道具商店', action=1),
        Button('💰首领商店', '首领商店', '💰首领商店', action=1),
        Button('✅我的道具', '我的道具', '✅我的道具', action=1),
        Button('💰查看交易所', '查看交易所', '💰查看交易所', action=1),
        Button('✅购买道具', '购买道具', '✅购买道具', action=2),
        Button('✅回收道具', '回收道具', '✅回收道具', action=2),
        Button('✅道具信息', '道具信息', '✅道具信息', action=2),
        Button('✅使用道具', '使用道具', '✅使用道具', action=2),
        Button('购买随机精灵蛋', '购买随机精灵蛋', '购买随机精灵蛋', action=1),
    ]
    await bot.send_option(msg, buttons)


@sv_pokemon_prop.on_fullmatch(['道具商店'])
async def prop_shop_list(bot, ev: Event):
    uid = ev.user_id

    mychenghao, huizhang = await get_chenghao(uid)

    my_score = await SCORE.get_score(uid)
    mes = f'我的金币:{my_score}\n商品列表(商品随得到的徽章增多)\n'
    propinfolist = ''
    for propinfo in proplist:
        if (
            proplist[propinfo]['score'] > 0
            and huizhang >= proplist[propinfo]['huizhang']
        ):
            propinfolist += f"{propinfo} [{proplist[propinfo]['type']}] 售价:{proplist[propinfo]['score']}\n"
    if propinfolist == '':
        mes = '商店暂时没有出售的物品，去挑战道馆试试吧'
        buttons = [
            Button('挑战道馆', '挑战道馆', action=1),
        ]
    else:
        mes += propinfolist
        buttons = [
            Button('✅购买道具', '购买道具', '✅购买道具', action=2),
            Button('📖道具信息', '道具信息', '📖道具信息', action=2),
        ]
    await bot.send_option(mes, buttons)

@sv_pokemon_prop.on_fullmatch(('首领商店','boss商店'))
async def prop_boss_list(bot, ev: Event):
    uid = ev.user_id

    my_score = await SCORE.get_shengwang(uid)
    mes = f'我的首领币:{my_score}\n物品列表\n'
    propinfolist = ''
    for propinfo in bossproplist:
        propinfolist += f"{propinfo} [{bossproplist[propinfo]['type']}] 售价:{bossproplist[propinfo]['score']}\n"
    mes += propinfolist
    buttons = [
        Button('✅兑换道具', '兑换道具', '✅兑换道具', action=2),
        Button('📖道具信息', '道具信息', '📖道具信息', action=2),
    ]
    await bot.send_option(mes, buttons)

@sv_pokemon_prop.on_command(['道具信息'])
async def prop_info(bot, ev: Event):
    args = ev.text.split()
    if len(args) != 1:
        return await bot.send('请输入 道具信息+道具名称', at_sender=True)
    propname = args[0]
    uid = ev.user_id
    mychenghao, huizhang = await get_chenghao(uid)
    try:
        propinfo = proplist[propname]
        mes = f"名称：{propname}\n类型：{propinfo['type']}\n描述：{propinfo['content']}"
        if propinfo['score'] > 0:
            mes += f"\n售价：{propinfo['score']}"
        if propinfo['score'] > 0 and int(huizhang) >= propinfo['huizhang']:
            buttons = [
                Button('✅购买道具', f'购买道具 {propname}', '✅购买道具', action=2),
            ]
            await bot.send_option(mes, buttons)
        else:
            await bot.send(mes)
    except:
        return await bot.send(
            '无法找到该道具，请输入正确的道具名称。', at_sender=True
        )

@sv_pokemon_prop.on_command(['购买随机精灵蛋'])
async def buy_random_egg(bot, ev: Event):
    args = ev.text.split()
    if len(args)<1:
        num = 1
    else:
        num = int(args[0])
    if num < 1:
        return await bot.send('请输入正确的数量', at_sender=True)
    uid = ev.user_id
    if not daily_random_egg.check(uid):
        return await bot.send(
            '今天的购买次数已经超过上限了哦，明天再来吧。', at_sender=True
        )
    need_score = num * 100000
    my_score = await SCORE.get_score(uid)
    if my_score < need_score:
        return await bot.send(f'随机精灵蛋需要金币{need_score},您的金币不足',at_sender=True)
    mapinfo = await POKE._get_map_now(uid)
    name = mapinfo[2]
    mes = f'{name}\n'
    chara_id_list = list(CHARA_NAME.keys())
    for jinyongid in jinyonglist_random_egg:
        chara_id_list.remove(jinyongid)
    egg_num = daily_random_egg.get_num(uid)
    add_egg_num = 0
    for i in range(0,num):
        get_day_num = add_egg_num + int(egg_num)
        if get_day_num >= 50:
            break
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
            zx_min = 530
            zx_max = 999
        find_flag = 0
        while find_flag == 0:
            random.shuffle(chara_id_list)
            pokemonid = chara_id_list[0]
            pokemon_zz = int(POKEMON_LIST[pokemonid][1]) + int(POKEMON_LIST[pokemonid][2]) + int(POKEMON_LIST[pokemonid][3]) + int(POKEMON_LIST[pokemonid][4]) + int(POKEMON_LIST[pokemonid][5]) + int(POKEMON_LIST[pokemonid][6])
            if pokemon_zz <= zx_max and pokemon_zz >= zx_min:
                find_flag = 1
                eggid = await get_pokemon_eggid(pokemonid)
                await SCORE.update_score(uid, -100000)
                await POKE._add_pokemon_egg(uid, eggid, 1)
                add_egg_num = add_egg_num + 1
        if pokemonid in jinyonglist:
            mes += f'您花费了100000金币，获得了{CHARA_NAME[eggid][0]}精灵蛋🎉🎉\n'
        else:
            mes += f'您花费了100000金币，获得了{CHARA_NAME[eggid][0]}精灵蛋\n'
    daily_random_egg.increase(uid, add_egg_num)
    buttons = [
        Button('✅再开一个', '购买随机精灵蛋', '✅再开一个', action=1),
        Button('📖宝可梦孵化', '宝可梦孵化', '📖宝可梦孵化', action=2),
        Button('📖我的精灵蛋', '我的精灵蛋', '📖我的精灵蛋', action=1),
    ]
    await bot.send_option(mes, buttons)

@sv_pokemon_prop.on_command(['回收道具'])
async def prop_send(bot, ev: Event):
    args = ev.text.split()
    if len(args) < 1:
        return await bot.send(
            '请输入 回收道具+道具名称+道具数量 用空格隔开', at_sender=True
        )
    propname = args[0]
    if len(args) == 2:
        propnum = int(args[1])
    else:
        propnum = 1
    uid = ev.user_id
    if propnum < 1:
        return await bot.send('请输入正确的道具数量', at_sender=True)
    mypropnum = await POKE._get_pokemon_prop(uid, propname)
    if mypropnum < propnum:
        return await bot.send('道具不足', at_sender=True)
    mychenghao, huizhang = await get_chenghao(uid)
    propinfo = proplist[propname]
    if propinfo['score'] == 0:
        pay_score = 100
    else:
        pay_score = int(propinfo['score'] * 0.3)
    get_score = pay_score * propnum
    await SCORE.update_score(uid, get_score)
    await POKE._add_pokemon_prop(uid, propname, 0 - propnum)
    mes = f'您回收了{propname}x{propnum}获得金币{get_score}'
    await bot.send(mes)
    
@sv_pokemon_prop.on_command(['购买道具'])
async def prop_buy(bot, ev: Event):
    args = ev.text.split()
    if len(args) < 1:
        return await bot.send(
            '请输入 购买道具+道具名称+道具数量 用空格隔开', at_sender=True
        )
    propname = args[0]
    if len(args) == 2:
        propnum = int(args[1])
    else:
        propnum = 1
    uid = ev.user_id
    if propnum < 1:
        return await bot.send('请输入正确的道具数量', at_sender=True)
    mychenghao, huizhang = await get_chenghao(uid)
    try:
        propinfo = proplist[propname]
        if propinfo['score'] == 0:
            return await bot.send('无法购买该道具', at_sender=True)
        my_score = await SCORE.get_score(uid)
        use_score = propinfo['score'] * propnum
        if propinfo['huizhang'] > int(huizhang):
            return await bot.send(
                f"需要{propinfo['huizhang']}枚徽章才能开放{propname}的购买",
                at_sender=True,
            )
        if use_score > my_score:
            return await bot.send(
                f'购买{propnum}件{propname}需要金币{use_score},您的金币不足',
                at_sender=True,
            )
        await SCORE.update_score(uid, 0 - use_score)
        await POKE._add_pokemon_prop(uid, propname, propnum)
        mes = f'恭喜！您花费了{use_score}金币成功购买了{propnum}件{propname}'
        if propinfo['type'] == '消耗品':
            buttons = [
                Button('✅使用道具', f'使用道具 {propname}', '✅使用道具', action=2),
            ]
            await bot.send_option(mes, buttons)
        else:
            await bot.send(mes)
    except:
        return await bot.send(
            '无法找到该道具，请输入正确的道具名称。', at_sender=True
        )

@sv_pokemon_prop.on_command(['兑换道具'])
async def boss_prop_buy(bot, ev: Event):
    args = ev.text.split()
    if len(args) < 1:
        return await bot.send(
            '请输入 兑换道具+道具名称+道具数量 用空格隔开', at_sender=True
        )
    propname = args[0]
    if len(args) == 2:
        propnum = int(args[1])
    else:
        propnum = 1
    if propnum < 1:
        return await bot.send('请输入正确的道具数量', at_sender=True)
    uid = ev.user_id
    try:
        propinfo = bossproplist[propname]
        my_score = await SCORE.get_shengwang(uid)
        use_score = propinfo['score'] * propnum
        if use_score > my_score:
            return await bot.send(
                f'购买{propnum}件{propname}需要首领币{use_score},您的首领币不足',
                at_sender=True,
            )
        await SCORE.update_shengwang(uid, 0 - use_score)
        if propinfo['type'] == '消耗品' or propinfo['type'] == 'Z纯晶':
            await POKE._add_pokemon_prop(uid, propname, propnum)
            mes = f'恭喜！您花费了{use_score}首领币成功购买了{propnum}件{propname}'
            buttons = [
                Button('✅使用道具', f'使用道具 {propname}', '✅使用道具', action=2),
            ]
        if propinfo['type'] == '精灵蛋':
            await POKE._add_pokemon_egg(uid, int(propinfo['name']), propnum)
            mes = f'恭喜！您花费了{use_score}首领币成功购买了{propname}x{propnum}'
            buttons = [
                Button('✅精灵孵化', f"宝可梦孵化{CHARA_NAME[int(propinfo['name'])][0]}", '✅精灵孵化', action=1),
            ]
        if propinfo['type'] == '学习机':
            await POKE._add_pokemon_technical(uid, propname, propnum)
            mes = f'恭喜！您花费了{use_score}首领币成功购买了{propname}学习机x{propnum}'
            buttons = [
                Button('✅学习技能', f'学习技能', '✅学习技能', action=2),
            ]
        await bot.send_option(mes, buttons)
    except:
        return await bot.send(
            '无法找到该道具，请输入正确的道具名称。', at_sender=True
        )

@sv_pokemon_prop.on_command(['携带道具'])
async def prop_xiedai(bot, ev: Event):
    args = ev.text.split()
    uid = ev.user_id
    if len(args) != 2:
        return await bot.send('请输入 携带道具+道具名称+精灵名 用空格隔开',at_sender=True,)
    propname = args[0]
    pokename = args[1]
    bianhao = await get_poke_bianhao(pokename)
    if bianhao == 0:
        return await bot.send('请输入正确的宝可梦名称。', at_sender=True)
    propkeylist = proplist.keys()
    if propname not in propkeylist:
        return await bot.send(
            '无法找到该道具，请输入正确的道具名称。', at_sender=True
        )
    propinfo = proplist[propname]
    if propinfo['type'] != 'Z纯晶' and propinfo['type'] != '进化石':
        return await bot.send(
            '该道具无法携带，请替换其他道具。', at_sender=True
        )
    mypropnum = await POKE._get_pokemon_prop(uid, propname)
    if mypropnum == 0:
        return await bot.send(f'您还没有{propname}哦。', at_sender=True)
    pokemon_info = await get_pokeon_info(uid, bianhao)
    if pokemon_info == 0:
        return await bot.send(
            f'您还没有{CHARA_NAME[bianhao][0]}。', at_sender=True
        )
    mes = f"您的宝可梦{CHARA_NAME[bianhao][0]}"
    if pokemon_info[16] is not None or pokemon_info[16] != '':
        if pokemon_info[16] in propkeylist:
            mes += f"\n取下了道具{pokemon_info[16]}"
            await POKE._add_pokemon_prop(uid, pokemon_info[16] , 1)
    mes += f"\n携带了道具{propname}"
    await POKE._add_pokemon_prop(uid, propname, -1)
    await POKE._add_pokemon_xiedai(uid, bianhao, propname)
    await bot.send(mes, at_sender=True)

@sv_pokemon_prop.on_command(['取下道具'])
async def prop_xiedai_del(bot, ev: Event):
    args = ev.text.split()
    uid = ev.user_id
    if len(args) != 1:
        return await bot.send('请输入 取下道具+精灵名 用空格隔开',at_sender=True,)
    pokename = args[0]
    bianhao = await get_poke_bianhao(pokename)
    if bianhao == 0:
        return await bot.send('请输入正确的宝可梦名称。', at_sender=True)
    pokemon_info = await get_pokeon_info(uid, bianhao)
    if pokemon_info == 0:
        return await bot.send(
            f'您还没有{CHARA_NAME[bianhao][0]}。', at_sender=True
        )
    if pokemon_info[16] is None or pokemon_info[16] == '':
        return await bot.send('您的宝可梦没有携带道具哦。', at_sender=True)
    propkeylist = proplist.keys()
    if pokemon_info[16] in propkeylist:
        mes = f"您的宝可梦{CHARA_NAME[bianhao][0]}"
        mes += f"\n取下了道具{pokemon_info[16]}"
        await POKE._add_pokemon_prop(uid, pokemon_info[16] , 1)
        await POKE._add_pokemon_xiedai(uid, bianhao, '')
        await bot.send(mes, at_sender=True)
    else:
        return await bot.send('您的宝可梦没有携带道具哦。', at_sender=True)

@sv_pokemon_prop.on_command(['使用道具'])
async def prop_use(bot, ev: Event):
    args = ev.text.split()
    if len(args) < 2:
        return await bot.send(
            '请输入 使用道具+道具名称+精灵名+道具数量 用空格隔开',
            at_sender=True,
        )
    propname = args[0]
    pokename = args[1]
    if len(args) == 3 and propname != '银色王冠':
        propnum = int(args[2])
    else:
        propnum = 1
    uid = ev.user_id

    bianhao = await get_poke_bianhao(pokename)
    if bianhao == 0:
        return await bot.send('请输入正确的宝可梦名称。', at_sender=True)
    pokemon_info = await get_pokeon_info(uid, bianhao)
    if pokemon_info == 0:
        return await bot.send(
            f'您还没有{CHARA_NAME[bianhao][0]}。', at_sender=True
        )

    propkeylist = proplist.keys()
    if propname not in propkeylist:
        return await bot.send(
            '无法找到该道具，请输入正确的道具名称。', at_sender=True
        )
    propinfo = proplist[propname]
    if propinfo['type'] == '进化':
        return await bot.send(
            '进化类道具无法直接使用，进华时会自动消耗。', at_sender=True
        )
    if propinfo['use'][0] == '性格':
        propnum = 1
    mypropnum = await POKE._get_pokemon_prop(uid, propname)
    if mypropnum == 0:
        return await bot.send(f'您还没有{propname}哦。', at_sender=True)
    if mypropnum < propnum:
        return await bot.send(
            f'您的{propname}数量小于{propnum}，使用失败。', at_sender=True
        )
    if propnum < 1:
        return await bot.send('请输入正确的道具数量', at_sender=True)
    buttons = [
        Button('📖精灵状态', f'精灵状态{pokename}', action=1),
    ]
    if propinfo['use'][0] == '性格':
        if pokemon_info[13] == propinfo['use'][1]:
            return await bot.send(
                f'您的{CHARA_NAME[bianhao][0]}的性格已经是{pokemon_info[13]}了，使用失败。',
                at_sender=True,
            )
        await POKE._add_pokemon_xingge(uid, bianhao, propinfo['use'][1])
        await POKE._add_pokemon_prop(uid, propname, -1)
        mes = f"使用成功！您的{CHARA_NAME[bianhao][0]}的性格变成了{propinfo['use'][1]}。"
        await bot.send_option(mes, buttons)
    elif propinfo['use'][0] == '努力':
        if propinfo['use'][2] > 0:
            nl_z = (
                pokemon_info[7]
                + pokemon_info[8]
                + pokemon_info[9]
                + pokemon_info[10]
                + pokemon_info[11]
                + pokemon_info[12]
            )
            if nl_z >= 510:
                return await bot.send(
                    f'使用失败,{CHARA_NAME[bianhao][0]}的基础值已经无法再提升了。',
                    at_sender=True,
                )
            nl_index = int(propinfo['use'][1] + 7)
            if pokemon_info[nl_index] >= 252:
                return await bot.send(
                    f"使用失败,{CHARA_NAME[bianhao][0]}的{zhongzu_list[propinfo['use'][1]][1]}基础值已经无法再提升了。",
                    at_sender=True,
                )
            add_num = propnum * propinfo['use'][2]
            need_num = 252 - pokemon_info[nl_index]
            need_z = 510 - nl_z
            need_num = min(need_num,need_z)
            if add_num < need_num:
                use_peop_num = propnum
            else:
                use_peop_num = math.ceil(
                    propnum - (add_num - need_num) / propinfo['use'][2]
                )
            add_num = use_peop_num * propinfo['use'][2]
            add_num = min(add_num, need_z)
            change_nl = min(252, add_num + pokemon_info[nl_index])
            change_nl_num = change_nl - pokemon_info[nl_index]
            # print(nl_index)
            pokemon_info = list(pokemon_info)
            pokemon_info[nl_index] = change_nl

            await POKE._add_pokemon_nuli(
                uid,
                bianhao,
                pokemon_info[7],
                pokemon_info[8],
                pokemon_info[9],
                pokemon_info[10],
                pokemon_info[11],
                pokemon_info[12],
            )
            mes = f"使用成功！{CHARA_NAME[bianhao][0]}的{zhongzu_list[propinfo['use'][1]][1]}基础值提升了{change_nl_num}点"
            await POKE._add_pokemon_prop(uid, propname, 0 - use_peop_num)
            await bot.send_option(mes, buttons)
        else:
            nl_index = int(propinfo['use'][1] + 7)
            if pokemon_info[nl_index] == 0:
                return await bot.send(
                    f"使用失败,{CHARA_NAME[bianhao][0]}的{zhongzu_list[propinfo['use'][1]][1]}基础值已经无法再降低了。",
                    at_sender=True,
                )
            add_num = 0 - propnum * propinfo['use'][2]
            need_num = pokemon_info[nl_index]
            if add_num < need_num:
                use_peop_num = propnum
            else:
                use_peop_num = math.ceil(
                    propnum - (add_num - need_num) / (0 - propinfo['use'][2])
                )
            add_num = use_peop_num * propinfo['use'][2]
            change_nl = max(0, add_num + pokemon_info[nl_index])
            change_nl_num = pokemon_info[nl_index] - change_nl
            pokemon_info = list(pokemon_info)
            pokemon_info[nl_index] = change_nl

            await POKE._add_pokemon_nuli(
                uid,
                bianhao,
                pokemon_info[7],
                pokemon_info[8],
                pokemon_info[9],
                pokemon_info[10],
                pokemon_info[11],
                pokemon_info[12],
            )
            mes = f"使用成功！{CHARA_NAME[bianhao][0]}的{zhongzu_list[propinfo['use'][1]][1]}基础值降低了{change_nl_num}点"
            await POKE._add_pokemon_prop(uid, propname, 0 - use_peop_num)
            await bot.send_option(mes, buttons)
    elif propinfo['use'][0] == '升级':
        if propinfo['use'][1] == 'level':
            if pokemon_info[0] == 100:
                return await bot.send(
                    f'使用失败,{CHARA_NAME[bianhao][0]}的等级已经无法再提升了。',
                    at_sender=True,
                )
            add_level = propinfo['use'][2] * propnum
            need_level = 100 - pokemon_info[0]
            if add_level <= need_level:
                use_peop_num = propnum
            else:
                use_peop_num = math.ceil(
                    propnum - (add_level - need_level) / propinfo['use'][2]
                )
            add_level = use_peop_num * propinfo['use'][2]
            now_level = pokemon_info[0] + add_level
            await POKE._add_pokemon_level(uid, bianhao, now_level, 0)
            mes = (
                f'使用成功！{CHARA_NAME[bianhao][0]}的等级提升了{add_level}'
            )
            await POKE._add_pokemon_prop(uid, propname, 0 - use_peop_num)
            await bot.send_option(mes, buttons)
    elif propinfo['use'][0] == '个体':
        if propname == '金色王冠':
            my_pokemon_info = []
            my_pokemon_info.append(pokemon_info[0])
            for num in range(1, 7):
                my_pokemon_info.append(31)
            for num in range(7, 17):
                my_pokemon_info.append(pokemon_info[num])
            await POKE._add_pokemon_info(uid, bianhao, my_pokemon_info, pokemon_info[15])
            await POKE._add_pokemon_prop(uid, '金色王冠', -1)
            mes = (
                f'使用成功！{CHARA_NAME[bianhao][0]}的个体值提升到极限了'
            )
            await bot.send(mes)
        if propname == '银色王冠':
            up_list = ['生命','攻击','防御','特攻','特防','速度']
            up_key_list = {
                "生命":1,
                "攻击":2,
                "防御":3,
                "特攻":4,
                "特防":5,
                "速度":6,
            }
            up_name = args[2]
            if up_name not in up_list:
                mes = '请输入想要提升的能力生命/攻击/防御/特攻/特防/速度'
                return await bot.send(mes)
            my_pokemon_info = []
            my_pokemon_info.append(pokemon_info[0])
            for num in range(1, 17):
                my_pokemon_info.append(pokemon_info[num])
            my_pokemon_info[up_key_list[up_name]] = 31
            await POKE._add_pokemon_prop(uid, '银色王冠', -1)
            await POKE._add_pokemon_info(uid, bianhao, my_pokemon_info, pokemon_info[15])
            mes = (
                f'使用成功！{CHARA_NAME[bianhao][0]}的{up_name}个体值提升到极限了'
            )
            await bot.send(mes)

@sv_pokemon_prop.on_fullmatch(['我的道具'])
async def prop_my_list(bot, ev: Event):
    uid = ev.user_id

    myproplist = await POKE.get_pokemon_prop_list(uid)
    if myproplist == 0:
        return await bot.send('您还没有道具哦。', at_sender=True)
    mes = ''
    for propinfo in myproplist:
        mes += f'{propinfo[0]} 数量 {propinfo[1]}\n'
    buttons = [
        Button('📖道具信息', '道具信息', '📖道具信息', action=2),
        Button('✅使用道具', '使用道具', '✅使用道具', action=2),
    ]
    await bot.send_option(mes, buttons)

@sv_pokemon_prop.on_command(['我的学习机','我的技能机','我的招式学习机'])
async def technical_my_list(bot, ev: Event):
    page = ''.join(re.findall('^[a-zA-Z0-9_\u4e00-\u9fa5]+$', ev.text))
    if not page:
        page = 0
    else:
        page = int(page) - 1
    uid = ev.user_id

    technicalnum,technicallist = await POKE.get_pokemon_technical_list(uid,page)
    if technicalnum == 0:
        return await bot.send('您还没有招式学习机哦。', at_sender=True)
    page_num = math.floor(technicalnum / 30) + 1
    page = page + 1
    mes = '您的招式学习机为(按数量排序一页30个):'
    for propinfo in technicallist:
        mes += f'\n{propinfo[0]} 数量 {propinfo[1]}'
    if page_num > 1:
        mes += f'\n第({page}/{page_num})页'
    buttons = [
        Button('📖技能信息', '精灵技能信息', '📖技能信息', action=2),
        Button('📖学习技能', '学习技能', '📖学习技能', action=2),
    ]
    if page > 1:
        uppage = page - 1
        buttons.append(Button('⬅️上一页', f'我的学习机{uppage}', '⬅️上一页', action=1))
    if page_num > 1:
        buttons.append(Button(f'⏺️跳转({page}/{page_num})', '我的学习机', f'⏺️跳转({page}/{page_num})', action=2))
    if page < page_num:
        dowmpage = page + 1
        buttons.append(Button('➡️下一页', f'我的学习机{dowmpage}', '➡️下一页', action=1))
    await bot.send_option(mes, buttons)

@sv_pokemon_prop.on_command(['交易所上架'])
async def exchange_up_prop(bot, ev: Event):
    #交易所上架 道具 奇异甜食 5 500
    uid = ev.user_id
    args = ev.text.split()
    if len(args) != 4:
        return await bot.send('请输入 交易所上架[类型][名称][数量][单价] 中间用空格分隔。\n如 交易所上架 精灵蛋 皮丘 5 8888', at_sender=True)
    proptype = args[0]
    if proptype not in ['道具','精灵蛋','宝可梦蛋','蛋']:
        return await bot.send('请输入正确的类型 道具/精灵蛋。', at_sender=True)
    propname = args[1]
    propnum = int(args[2])
    if propnum < 1:
        return await bot.send('上架商品的数量需大于1。', at_sender=True)
    score = int(args[3])
    if score < 10:
        return await bot.send('上架商品的价格需大于10。', at_sender=True)
    string = "0123456789"
    random_list = random.sample(list(string), 8)
    exchangeid = ''.join(random_list)
    if proptype == '道具':
        propkeylist = proplist.keys()
        if propname not in propkeylist:
            return await bot.send('无法找到该道具，请输入正确的道具名称。', at_sender=True)
        mypropnum = await POKE._get_pokemon_prop(uid, propname)
        if mypropnum == 0:
            return await bot.send(f'您还没有{propname}哦。', at_sender=True)
        if mypropnum < propnum:
            return await bot.send(f'您的{propname}数量小于{propnum}，上架失败。', at_sender=True)
        now_time = math.ceil(time.time())
        await POKE.new_exchange(exchangeid,proptype,propname,propnum,uid,score,now_time)
        await POKE._add_pokemon_prop(uid, propname, 0 - propnum)
        mes = f'您以单价{score}的价格成功上架了{propname}x{propnum}。'
    if proptype == '精灵蛋' or proptype == '宝可梦蛋' or proptype == '蛋':
        proptype = '精灵蛋'
        bianhao = await get_poke_bianhao(propname)
        if bianhao == 0:
            return await bot.send('请输入正确的宝可梦名称。', at_sender=True)
        egg_num = await POKE.get_pokemon_egg(uid, bianhao)
        if egg_num == 0:
            return await bot.send(f'您还没有{pokename}的精灵蛋哦。', at_sender=True)
        if egg_num < propnum:
            return await bot.send(f'您的{pokename}精灵蛋数量小于{propnum}，上架失败。', at_sender=True)
        now_time = math.ceil(time.time())
        await POKE.new_exchange(exchangeid,'精灵蛋',bianhao,propnum,uid,score,now_time)
        await POKE._add_pokemon_egg(uid, bianhao, 0 - propnum)
        mes = f'您以单价{score}的价格成功上架了{propname}精灵蛋x{propnum}。'
    buttons = [
        Button('💰寄售商品','交易所上架', '💰寄售商品', action=2),
        Button('💰购买商品','交易所购买', '💰购买商品', action=2),
        Button('💰我的寄售','我的寄售', '💰我的寄售', action=1),
        Button('💰查看交易所', '查看交易所', '💰查看交易所', action=1),
        Button('💰交易所筛选', '查看交易所', '💰交易所筛选', action=2),
    ]
    await bot.send_option(mes, buttons)

@sv_pokemon_prop.on_command(['交易所下架'])
async def exchange_down_prop(bot, ev: Event):
    args = ev.text.split()
    if len(args) != 1:
        return await bot.send('请输入 交易所下架[商品ID]', at_sender=True)
    exchangeid = args[0]
    uid = ev.user_id
    exchange_info = await POKE._get_exchange_info(exchangeid)
    if exchange_info == 0:
        return await bot.send('请输入正确的商品ID或该商品已售出', at_sender=True)
    if exchange_info[3] != uid:
        return await bot.send('您不是该商品的上架人，无法执行下架操作', at_sender=True)
    if exchange_info[0] == '道具':
        await POKE._add_pokemon_prop(uid, exchange_info[1], int(exchange_info[2]))
        mes = f'您下架了{exchange_info[1]}{exchange_info[0]}x{exchange_info[2]}。'
    if exchange_info[0] == '精灵蛋':
        await POKE._add_pokemon_egg(uid, int(exchange_info[1]), int(exchange_info[2]))
        mes = f'您下架了{CHARA_NAME[int(exchange_info[1])][0]}{exchange_info[0]}x{exchange_info[2]}。'
    await POKE.delete_exchange(exchangeid)
    buttons = [
        Button('💰寄售商品','交易所上架', '💰寄售商品', action=2),
        Button('💰购买商品','交易所购买', '💰购买商品', action=2),
        Button('💰我的寄售','我的寄售', '💰我的寄售', action=1),
        Button('💰查看交易所', '查看交易所', '💰查看交易所', action=1),
        Button('💰交易所筛选', '查看交易所', '💰交易所筛选', action=2),
    ]
    await bot.send_option(mes, buttons)

@sv_pokemon_prop.on_command(['查看交易所'])
async def show_exchange_list(bot, ev: Event):
    args = ev.text.split()
    upbutton = ''
    downbutton = ''
    if len(args) > 0:
        if args[0].isdigit():
            page = int(args[0]) - 1
            exchangenum,exchange_list = await POKE.get_exchange_list(page)
            page_num = math.floor(exchangenum / 30) + 1
            if page > 0:
                upbutton = f'查看交易所{page}'
            if page_num > page + 1:
                downbutton = f'查看交易所{page+2}'
        else:
            proptype = args[0]
            if proptype not in ['道具','精灵蛋']:
                return await bot.send('请输入正确的类型 道具/精灵蛋。', at_sender=True)
            if len(args) == 1:
                page = 0
                exchangenum,exchange_list = await POKE.get_exchange_list_sx_type(proptype,page)
                page_num = math.floor(exchangenum / 30) + 1
                if page > 0:
                    upbutton = f'查看交易所{proptype} {page}'
                if page_num > page + 1:
                    downbutton = f'查看交易所{proptype} {page+2}'
            else:
                if args[1].isdigit():
                    page = int(args[1]) - 1
                    exchangenum,exchange_list = await POKE.get_exchange_list_sx_type(proptype,page)
                    page_num = math.floor(exchangenum / 30) + 1
                    if page > 0:
                        upbutton = f'查看交易所{proptype} {page}'
                    if page_num > page + 1:
                        downbutton = f'查看交易所{proptype} {page+2}'
                else:
                    propname = args[1]
                    if proptype == '精灵蛋':
                        exchangename = await get_poke_bianhao(propname)
                    else:
                        exchangename = propname
                    page = 0
                    if len(args) == 2:
                        exchangenum,exchange_list = await POKE.get_exchange_list_sx_name(proptype,exchangename,page)
                        page_num = math.floor(exchangenum / 30) + 1
                        if page > 0:
                            upbutton = f'查看交易所{proptype} {propname} {page}'
                        if page_num > page + 1:
                            downbutton = f'查看交易所{proptype} {propname} {page+2}'
                    if len(args) == 3:
                        page = int(args[2]) - 1
                        exchangenum,exchange_list = await POKE.get_exchange_list_sx_name(proptype,exchangename,page)
                        page_num = math.floor(exchangenum / 30) + 1
                        if page > 0:
                            upbutton = f'查看交易所{proptype} {propname} {page}'
                        if page_num > page + 1:
                            downbutton = f'查看交易所{proptype} {propname} {page+2}'
    else:
        page = 0
        exchangenum,exchange_list = await POKE.get_exchange_list(page)
        page_num = math.floor(exchangenum / 30) + 1
        if page > 0:
            upbutton = f'查看交易所{page}'
        if page_num > page + 1:
            downbutton = f'查看交易所{page+2}'
    if exchangenum == 0:
        return await bot.send('当前交易所没有寄售中的商品', at_sender=True)
    mes = '当前寄售中的商品为\n商品ID 类型 名称 数量 单价'
    for exchangeinfo in exchange_list:
        mes += f'\n{exchangeinfo[0]} {exchangeinfo[1]}'
        propname = exchangeinfo[2]
        if exchangeinfo[1] == '精灵蛋':
            propname = CHARA_NAME[int(exchangeinfo[2])][0]
        mes += f' {propname} {exchangeinfo[3]} {exchangeinfo[4]}'
    if page_num > 1:
        mes += f'\n第({page + 1}/{page_num})页'
    buttons = [
        Button('💰我的寄售','我的寄售', '💰我的寄售', action=1),
        Button('💰寄售商品','交易所上架', '💰寄售商品', action=2),
        Button('💰购买商品','交易所购买', '💰购买商品', action=2),
    ]
    if upbutton != '':
        buttons.append(Button('上一页',f'{upbutton}', '上一页', action=2))
    if downbutton != '':
        buttons.append(Button('下一页',f'{downbutton}', '下一页', action=2))
    await bot.send_option(mes, buttons)

@sv_pokemon_prop.on_command(['交易所购买'])
async def exchange_buy_prop(bot, ev: Event):
    args = ev.text.split()
    if len(args) < 1:
        return await bot.send('请输入 交易所购买[商品ID][数量] 用空格分隔，数量默认为1', at_sender=True)
    exchangeid = args[0]
    uid = ev.user_id
    exchange_info = await POKE._get_exchange_info(exchangeid)
    if exchange_info == 0:
        return await bot.send('请输入正确的商品ID或该商品已售出', at_sender=True)
    if len(args) == 2:
        buy_num = int(args[1])
    else:
        buy_num = 1
    if buy_num < 1:
        return await bot.send('请输入正确的道具数量', at_sender=True)
    if buy_num > int(exchange_info[2]):
        return await bot.send(f'寄售中物品数量不足{buy_num}，请重新输入数量', at_sender=True)
    need_score = buy_num * int(exchange_info[4])
    my_score = await SCORE.get_score(uid)
    if need_score > my_score:
        if exchange_info[0] == '精灵蛋':
            return await bot.send(f'购买{buy_num}件{CHARA_NAME[int(exchange_info[1])][0]}{exchange_info[0]}需要金币{need_score}，您的金币不足', at_sender=True)
        if exchange_info[0] == '道具':
            return await bot.send(f'购买{buy_num}件{exchange_info[1]}需要金币{need_score}，您的金币不足', at_sender=True)
    if buy_num == int(exchange_info[2]):
        await POKE.delete_exchange(exchangeid)
    else:
        await POKE.update_exchange(exchangeid, 0 - buy_num)
    if exchange_info[0] == '道具':
        await POKE._add_pokemon_prop(uid, exchange_info[1], buy_num)
        mes = f'您花费了{need_score}金币，成功购买了{exchange_info[1]}{exchange_info[0]}x{buy_num}。'
    if exchange_info[0] == '精灵蛋':
        await POKE._add_pokemon_egg(uid, int(exchange_info[1]), buy_num)
        mes = f'您花费了{need_score}金币，成功购买了{CHARA_NAME[int(exchange_info[1])][0]}{exchange_info[0]}x{buy_num}。'
    await SCORE.update_score(uid, 0 - need_score)
    get_score = math.ceil(need_score * 0.9)
    await SCORE.update_score(exchange_info[3], get_score)
    buttons = [
        Button('💰寄售商品','交易所上架', '💰寄售商品', action=2),
        Button('💰购买商品','交易所购买', '💰购买商品', action=2),
        Button('💰我的寄售','我的寄售', '💰我的寄售', action=1),
        Button('💰查看交易所', '查看交易所', '💰查看交易所', action=1),
        Button('💰交易所筛选', '查看交易所', '💰交易所筛选', action=2),
    ]
    await bot.send_option(mes, buttons)

@sv_pokemon_prop.on_command(['我的寄售'])
async def show_exchange_list_my(bot, ev: Event):
    args = ev.text.split()
    upbutton = ''
    downbutton = ''
    uid = ev.user_id
    if len(args) > 0:
        page = int(args[0]) - 1
        exchangenum,exchange_list = await POKE.get_exchange_list_my(uid,page)
        page_num = math.floor(exchangenum / 30) + 1
        if page > 0:
            upbutton = f'我的寄售{page}'
        if page_num > page + 1:
            downbutton = f'我的寄售{page+2}'
    else:
        page = 0
        exchangenum,exchange_list = await POKE.get_exchange_list_my(uid,page)
        page_num = math.floor(exchangenum / 30) + 1
        if page > 0:
            upbutton = f'我的寄售{page}'
        if page_num > page + 1:
            downbutton = f'我的寄售{page+2}'
    if exchangenum == 0:
        return await bot.send('您没有寄售中的商品', at_sender=True)
    mes = '您当前寄售中的商品为\n商品ID 类型 名称 数量 单价'
    for exchangeinfo in exchange_list:
        mes += f'\n{exchangeinfo[0]} {exchangeinfo[1]}'
        propname = exchangeinfo[2]
        if exchangeinfo[1] == '精灵蛋':
            propname = CHARA_NAME[int(exchangeinfo[2])][0]
        mes += f' {propname} {exchangeinfo[3]} {exchangeinfo[4]}'
    if page_num > 1:
        mes += f'\n第({page + 1}/{page_num})页'
    buttons = [
        Button('💰寄售商品','交易所上架', '💰寄售商品', action=2),
        Button('💰购买商品','交易所购买', '💰购买商品', action=2),
    ]
    if upbutton != '':
        buttons.append(Button('上一页',f'{upbutton}', '上一页', action=2))
    if downbutton != '':
        buttons.append(Button('下一页',f'{downbutton}', '下一页', action=2))
    await bot.send_option(mes, buttons)

@sv_pokemon_prop_sp.on_command(['pm发红包'])
async def mew_pm_hongbao(bot, ev: Event):
    uid = ev.user_id
    args = ev.text.split()
    if len(args) < 3:
        return await bot.send('请输入 pm发红包[红包口令][红包金额][红包数量] 用空格分隔', at_sender=True)
    kouling = args[0]
    score = int(args[1])
    num = int(args[2])
    if score < 1:
        return await bot.send('红包金额需要大于0', at_sender=True)
    if num < 1:
        return await bot.send('红包数量需要大于0', at_sender=True)
    if num > score:
        return await bot.send('红包数量需要大于红包金额', at_sender=True)
    my_score = await SCORE.get_score(uid)
    if score > my_score:
        return await bot.send(f'您的金币小于{score}，红包发放失败', at_sender=True)
    hbscore,use_score,hbnum,use_num,openuser = pmhongbao.get_hongbao(kouling)
    if hbscore > 0:
        return await bot.send(f'红包口令重复，红包发放失败', at_sender=True)
    pmhongbao.insert_hongbao(kouling,score,num)
    await SCORE.update_score(uid, 0 - score)
    mes = f'红包发放成功，红包口令：{kouling}'
    buttons = [
        Button('抢红包', f'pm抢红包{kouling}', '抢红包', action=1),
    ]
    await bot.send_option(mes, buttons)
    
@sv_pokemon_prop.on_command(['pm抢红包'])
async def open_pm_hongbao(bot, ev: Event):
    uid = ev.user_id
    args = ev.text.split()
    if len(args) < 1:
        return await bot.send('请输入 pm抢红包[红包口令]', at_sender=True)
    kouling = args[0]
    score,use_score,num,use_num,openuser = pmhongbao.get_hongbao(kouling)
    if uid in openuser:
        return await bot.send('您已经抢过该红包', at_sender=True)
    if score == 0:
        return await bot.send('红包口令无效或该红包已被抢完', at_sender=True)
    
    mapinfo = await POKE._get_map_now(uid)
    name = mapinfo[2]
    last_score = score - use_score
    last_num = int(num) - int(use_num)
    max_score = (last_score/last_num)*1.5
    if last_num == 0 or last_score == 0:
        return await bot.send('该红包已被抢完', at_sender=True)
    if last_num == 1:
        get_score = last_score
    else:
        get_score = int(math.floor(random.uniform(1, max_score)))
    await SCORE.update_score(uid, get_score)
    pmhongbao.open_hongbao(kouling,get_score,uid)
    if last_num == 1:
        pmhongbao.hongbao_off(kouling)
    mes = f'【{name}】恭喜！您抢到了{get_score}金币，红包剩余数量{last_num - 1}，剩余金额{last_score - get_score}'
    buttons = [
        Button('抢红包', f'pm抢红包{kouling}', '抢红包', action=1),
    ]
    await bot.send_option(mes, buttons)

@sv_pokemon_prop.on_command(['抽取道具'])
async def add_equip_gacha(bot, ev: Event):
    args = ev.text.split()      #文本提取
    uid = ev.user_id
    gacha_DUNDCORE = 10000  #单抽所需金币
    if len(args) == 1:
        if args[0].isdigit():
            gachanum = int(args[0])
        else:
            gachanum = 1
    else:
        gachanum = 1 
    
    if gachanum > 100:
        gachanum = 100

    need_score = gacha_DUNDCORE*gachanum
    my_score = await SCORE.get_score(uid)

    if need_score>my_score:
        return await bot.send(f'抽卡需要{need_score}金币\n您的金币不足：{my_score}，无法抽卡哦', at_sender=True)

    results = []
    total_weight = sum([info["weight"] for info in propgachalist.values()])
    for _ in range(gachanum):
        # 生成随机数，范围从1到总权重
        random_weight = int(math.floor(random.uniform(1, total_weight)))

        # 累加权重，直到找到对应的等级
        running_total = 0
        tier = None
        for tier_name, info in propgachalist.items():
            running_total += info["weight"]
            if random_weight <= running_total:
                tier = tier_name
                break

        # 从对应的等级中随机选取一张卡牌
        propname = random.choice(propgachalist[tier]["names"])
        results.append(propname)
    
    result_count = Counter(results)
    get_gachalist = ''
    for propname, propnum in result_count.items():
        await POKE._add_pokemon_prop(uid, propname, propnum)
        showicon = ''
        for tier_name, info in propgachalist.items():
            if propname in info['names']:
                if tier_name == 'SSR' or tier_name == 'SSSR':
                    showicon = '🎉🎉'
        get_gachalist += f"\n{propname}: {propnum}个{showicon}"

    last_score = my_score - need_score
    await SCORE.update_score(uid, 0-need_score)
    msg = f"消耗{need_score}金币，剩余金币{last_score}\n累计抽取{gachanum}次获得的道具为：{get_gachalist}"
    buttons = [
        Button('✅兑换道具', '兑换道具', '✅兑换道具', action=2),
        Button('📖道具信息', '道具信息', '📖道具信息', action=2),
    ]
    await bot.send_option(msg, buttons)

# 每日0点执行交易所7天无销售商品自动下架
@scheduler.scheduled_job('cron', hour ='*')
async def down_exchange_day():
    now = datetime.now(pytz.timezone('Asia/Shanghai'))
    if now.hour not in [0]:
        return
    findtime = math.ceil(time.time()) - 259200
    exchange_list = await POKE.get_exchange_list_time(findtime)
    if exchange_list == 0:
        logger.info('今日无超时寄售商品，无需下架')
        return
    down_num = 0
    for exchange_info in exchange_list:
        if exchange_info[1] == '道具':
            await POKE._add_pokemon_prop(exchange_info[4], exchange_info[2], int(exchange_info[3]))
        if exchange_info[1] == '精灵蛋':
            await POKE._add_pokemon_egg(exchange_info[4], int(exchange_info[2]), int(exchange_info[3]))
        await POKE.delete_exchange(exchange_info[0])
        down_num += 1
    logger.info(f'今日已执行{down_num}件交易所超期商品下架')








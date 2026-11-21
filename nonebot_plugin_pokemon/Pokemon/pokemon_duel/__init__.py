import os
import re
import math

from nonebot_plugin_pokemon.compat.sv import SV
from nonebot_plugin_pokemon.compat.models import Event
from nonebot_plugin_pokemon.compat.message_models import Button
from nonebot_plugin_pokemon.compat.segment import MessageSegment
from nonebot_plugin_pokemon.compat.image import convert_img
from .map import *
from .prop import *
from .race import *
from .fight import *
from .until import *
from .pokeconfg import *
from .draw_image import draw_pokemon_info, draw_pokemon_info_tj
from ..utils.resource.RESOURCE_PATH import CHAR_ICON_PATH
from .data_source import make_jineng_use, jinengfuncs

sv_pokemon_duel = SV('宝可梦状态', priority=5)


@sv_pokemon_duel.on_fullmatch(('精灵帮助', '宝可梦帮助'))
async def pokemon_help(bot, ev: Event):
    mes = "宝可梦帮助\n特别注意！！！\n野外探索有内置的5秒CD,使用连点器的建议点击间隔设置成6秒,减少负载。提升流畅性\n特别注意！！！\n"
    mes += "进入游戏请先输入 领取初始精灵【精灵名】 开局，初始精灵有各个版本的御三家，如\n领取初始精灵小火龙\n"
    mes += "1.初始精灵列表 查看初始精灵列表\n"
    mes += "2.领取初始精灵 精灵名 领取初始精灵\n"
    mes += "3.我的精灵列表 查询我拥有的等级前20的精灵\n"
    mes += "4.放生精灵 精灵名 放生名为【精灵名】的精灵\n"
    mes += "5.学习技能 精灵名 技能名 让精灵学习技能\n"
    mes += "6.遗忘技能 精灵名 技能名 让精灵学习技能\n"
    mes += "7.野外探索 在野外地区与野生宝可梦或训练师战斗获取精灵经验\n"
    mes += "8.开启/关闭自动探索 野外自动探索\n"
    mes += "9.打工 在城镇地区打工进行打工赚取金币\n"
    mes += "10.前往 地点名 前往【地点名】的地点\n"
    mes += "11.宝可梦进化 精灵名 让你的宝可梦进化为【精灵名】，需要有前置进化型精灵\n"
    mes += "12.修改训练家名称 昵称 把你的训练家名称改为【昵称】，【昵称】有唯一性，作为对战识别符\n"
    mes += "13.查看地图关东|成都|丰缘|神奥|合众|卡洛斯|阿罗拉|伽勒尔|帕底亚 查看地图信息\n"
    mes += "14.我的精灵蛋 查询我的精灵蛋信息\n"
    mes += "15.重置个体值 精灵名 消耗一枚【精灵名】初始形态的精灵蛋对【精灵名】的个体值进行重置,后面跟数量可以进行多次重置\n"
    mes += "16.宝可梦孵化 精灵名 消耗一枚【精灵名】的精灵蛋孵化出一只lv.5的【精灵名】\n"
    mes += "17.更新队伍 精灵名 更新手持队伍信息，不同的宝可梦用空格分隔，最多4只\n"
    mes += "18.大量出现信息 查询当前随机出现的大量宝可梦消息\n"
    mes += "19.宝可梦重生 让等级到100级的精灵重生为精灵蛋\n"
    mes += "20.更新公告 查看最近更新内容\n"
    mes += "21.道具帮助 查看道具相关帮助\n"
    mes += "22.战斗帮助 查看战斗相关帮助\n"
    mes += "注:\n同一类型的精灵只能拥有一只:进化型为不同类型\n后续功能在写了在写了 新建文件夹\n其他宝可梦相关小游戏可以点击[小游戏帮助]查询"
    mes += "\n欢迎加入交流群：684118798"
    
    #await bot.send(mes)
    buttons = [
        Button('✅道具帮助', '道具帮助', '✅道具帮助', action=1),
        Button('✅战斗帮助', '战斗帮助', '✅战斗帮助', action=1),
        Button('📖精灵状态', '精灵状态', '📖精灵状态', action=2),
        Button('🔄更新队伍', '更新队伍', '🔄更新队伍', action=2),
        Button('✅领取初始精灵', '领取初始精灵', '✅领取初始精灵', action=2),
        Button('🏝️野外探索', '野外探索','🏝️野外探索', action=1),
        Button('🗺查看地图', '查看地图','🗺查看地图', action=1),
        Button('✅大量出现信息', '大量出现信息','✅大量出现信息', action=1),
        Button('✅小游戏帮助', '小游戏帮助','✅小游戏帮助', action=1),
        Button('✅支持作者', 'https://afdian.net/a/556186aa','✅支持作者', action=0),
    ]
    await bot.send_option(mes, buttons)

@sv_pokemon_duel.on_fullmatch(('更新公告', '查看公告'))
async def pokemon_gonggao(bot, ev: Event):
    msg = """
       宝可梦更新公告：
2024-8-21
1、完成战斗中mega进化系统
2024-8-20
1、尝试添加mega进化
2024-8-19
1、添加抽取道具
2、添加携带道具Z纯晶
3、添加Z招式的使用
2024-8-18
1、野外自动探索掉落算法完善
2、世界boss奖励结算完善按照伤即时给奖励
2024-8-17
1、添加野外自动探索
2024-6-10
1、添加精灵试炼塔挑战相关
2024-4-10
1、匹配对战中可以替换精灵
2024-4-9
1、完成匹配对战段位体系
2024-4-1
1、完成匹配对战
2024-3-20
1、添加帕底亚地区
2、首领挑战添加退出按钮
 """
    buttons = [
        Button('✅道具帮助', '道具帮助', '✅道具帮助', action=1),
        Button('✅战斗帮助', '战斗帮助', '✅战斗帮助', action=1),
        Button('📖精灵状态', '精灵状态', '📖精灵状态', action=2),
        Button('🔄更新队伍', '更新队伍', '🔄更新队伍', action=2),
        Button('✅领取初始精灵', '领取初始精灵', '✅领取初始精灵', action=2),
        Button('🏝️野外探索', '野外探索','🏝️野外探索', action=1),
        Button('🗺查看地图', '查看地图','🗺查看地图', action=1),
        Button('✅大量出现信息', '大量出现信息','✅大量出现信息', action=1),
        Button('✅小游戏帮助', '小游戏帮助','✅小游戏帮助', action=1),
        Button('✅支持作者', 'https://afdian.net/a/556186aa','✅支持作者', action=0),
    ]
    await bot.send_option(msg, buttons)
    
    
@sv_pokemon_duel.on_fullmatch(['小游戏帮助', '宝可梦小游戏帮助'])
async def pokemon_help_game(bot, ev: Event):
    msg = '宝可梦小游戏帮助\n游戏名：\n1、我是谁：宝可梦猜猜我是谁\n（给出宝可梦剪影，猜猜是哪只宝可梦）\n2、猜精灵：宝可梦信息猜猜\n（给出宝可梦的6条信息，猜猜是哪只宝可梦）\n3、猜属性：宝可梦属性猜测\n（给出5条属性的克制关系信息，猜猜是哪种属性组合）\n4、猜技能：宝可梦技能猜测\n（给给出技能的6条信息，猜猜是哪个技能）\n5、猜图鉴：根据图鉴猜精灵\n（给出图鉴信息，猜测使哪只精灵）\n注:\n其他的宝可梦小游戏正在火速开发中(新建文件夹)'
    mes = '宝可梦小游戏帮助\r<qqbot-cmd-input text="我是谁" show="我是谁" reference="false" />'
    buttons = [
        Button('✅我是谁', '我是谁', '✅我是谁', action=1),
        Button('✅猜精灵', '猜精灵', '✅猜精灵', action=1),
        Button('✅猜属性', '猜属性', '✅猜属性', action=1),
        Button('✅猜技能', '猜技能', '✅猜技能', action=1),
        Button('✅猜图鉴', '猜图鉴', '✅猜图鉴', action=1),
    ]
    await bot.send_option(msg, buttons)

@sv_pokemon_duel.on_command(('wsid', '虚拟id'))
async def get_my_qqgroup_id(bot, ev: Event):
    uid = ev.user_id
    gid = ev.group_id
    mes = f"群虚拟id为\n{gid}\n用户虚拟id为\n{uid}"
    await bot.send(mes)

@sv_pokemon_duel.on_command(('技能测试', '测试技能'))
async def get_jineng_use_text(bot, ev: Event):
    args = ev.text.split()
    if len(args) != 2:
        return await bot.send('请输入 技能测试+宝可梦名称+技能名称 中间用空格隔开。', at_sender=True)
    pokename1 = args[0]
    uid = ev.user_id
    bianhao1 = await get_poke_bianhao(pokename1)
    if bianhao1 == 0:
        return await bot.send('请输入正确的宝可梦名称。', at_sender=True)
    mypokemon_info = await get_pokeon_info(uid, bianhao1)
    if mypokemon_info == 0:
        return await bot.send(
            f'您还没有{CHARA_NAME[bianhao][0]}。', at_sender=True
        )
    myzhuangtai = [['无', 0], ['无', 0]]
    dizhuangtai = [['无', 0], ['无', 0]]
    changdi = [['无天气', 99], ['', 0]]
    myinfo = await new_pokemon_info(bianhao1, mypokemon_info)
    bianhao2 = 20
    dilevel = 100
    dipokemon_info = await get_pokeon_info_sj(bianhao2, dilevel)
    diinfo = await new_pokemon_info(bianhao2, dipokemon_info)
    jineng = args[1]
    mes,myinfo,diinfo,myzhuangtai,dizhuangtai,changdi = await make_jineng_use(jineng, myinfo, diinfo, myzhuangtai, dizhuangtai, changdi)
    await bot.send(mes)

@sv_pokemon_duel.on_command(('我的精灵列表', '我的宝可梦列表'))
async def my_pokemon_list(bot, ev: Event):
    page = ''.join(re.findall('^[a-zA-Z0-9_\u4e00-\u9fa5]+$', ev.text))
    if not page:
        page = 0
    else:
        page = int(page) - 1
    uid = ev.user_id

    pokemon_num = await POKE._get_pokemon_num(uid)
    if pokemon_num == 0:
        return await bot.send(
            '您还没有精灵，请输入 领取初始精灵+初始精灵名称 开局。',
            at_sender=True,
        )

    page_num = math.floor(pokemon_num / 30) + 1
    mypokelist = await POKE._get_pokemon_list(uid, page)
    mes = ''
    page = page + 1
    mes += f'<@{uid}>您的精灵信息为(按等级与编号排序一页30只):'
    for pokemoninfo in mypokelist:
        startype = await POKE.get_pokemon_star(uid, pokemoninfo[0])
        pokename = CHARA_NAME[pokemoninfo[0]][0]
        if ')' in pokename:
            pokename = pokename.replace(')','）')
        mes += f"\n{starlist[startype]}{CHARA_NAME[pokemoninfo[0]][0]} (Lv.{pokemoninfo[1]})"
        #mes += f" [状态] (mqqapi://aio/inlinecmd?command=精灵状态{pokename})"
    if page_num > 1:
        mes += f'\n第({page}/{page_num})页'
    buttons = [
        Button('📖精灵状态', '精灵状态', '📖精灵状态', action=2),
        Button('🔄更新队伍', '更新队伍', '🔄更新队伍', action=2),
    ]
    if page > 1:
        uppage = page - 1
        buttons.append(Button('⬅️上一页', f'我的精灵列表{uppage}', '⬅️上一页', action=1))
    if page_num > 1:
        buttons.append(Button(f'⏺️跳转({page}/{page_num})', '我的精灵列表', f'⏺️跳转({page}/{page_num})', action=2))
    if page < page_num:
        dowmpage = page + 1
        buttons.append(Button('➡️下一页', f'我的精灵列表{dowmpage}', '➡️下一页', action=1))
    await bot.send_option(mes, buttons)


@sv_pokemon_duel.on_command(('精灵图鉴', '宝可梦图鉴'))
async def show_poke_info(bot, ev: Event):
    args = ev.text.split()
    if len(args) != 1:
        return await bot.send('请输入 精灵图鉴+宝可梦名称 中间用空格隔开。', at_sender=True)
    pokename = args[0]
    pokename = pokename.replace('）',')').replace('（','(')
    uid = ev.user_id
    bianhao = await get_poke_bianhao(pokename)
    if bianhao == 0:
        return await bot.send('请输入正确的宝可梦名称。', at_sender=True)
    im, jinhualist = await draw_pokemon_info_tj(bianhao,0)
    
    buttons = []
    for jinhuainfo in jinhualist:
        buttons.append(
            Button(
                f'🔍︎{jinhuainfo[1]}',
                f'精灵图鉴{jinhuainfo[1]}',
                f'🔍︎{jinhuainfo[1]}',
                action=1,
            )
        )
    await bot.send_option(im, buttons)

@sv_pokemon_duel.on_command(('闪光图鉴', '闪光宝可梦图鉴'))
async def show_poke_info_star(bot, ev: Event):
    args = ev.text.split()
    if len(args) != 1:
        return await bot.send('请输入 闪光图鉴+宝可梦名称 中间用空格隔开。', at_sender=True)
    pokename = args[0]
    pokename = pokename.replace('）',')').replace('（','(')
    uid = ev.user_id
    bianhao = await get_poke_bianhao(pokename)
    if bianhao == 0:
        return await bot.send('请输入正确的宝可梦名称。', at_sender=True)
    im, jinhualist = await draw_pokemon_info_tj(bianhao,1)
    
    buttons = []
    for jinhuainfo in jinhualist:
        buttons.append(
            Button(
                f'🔍︎{jinhuainfo[1]}',
                f'闪光图鉴{jinhuainfo[1]}',
                f'🔍︎{jinhuainfo[1]}',
                action=1,
            )
        )
    await bot.send_option(im, buttons)

@sv_pokemon_duel.on_command(('精灵状态', '宝可梦状态'))
async def get_my_poke_info_t(bot, ev: Event):
    args = ev.text.split()
    if len(args) != 1:
        return await bot.send('请输入 精灵状态+宝可梦名称 中间用空格隔开。', at_sender=True)
    pokename = args[0]
    pokename = pokename.replace('）',')').replace('（','(')
    uid = ev.user_id
    bianhao = await get_poke_bianhao(pokename)
    if bianhao == 0:
        return await bot.send('请输入正确的宝可梦名称。', at_sender=True)
    pokemon_info = await get_pokeon_info(uid, bianhao)
    if pokemon_info == 0:
        return await bot.send(
            f'您还没有{CHARA_NAME[bianhao][0]}。', at_sender=True
        )
    im, jinhualist = await draw_pokemon_info(uid, pokemon_info, bianhao)
    buttons = [
        Button('📖查图鉴', f'精灵图鉴{pokename}', '📖查图鉴', action=1),
        Button('📖学技能', f'学习技能{pokename}', '📖学技能', action=2),
        Button('📖遗忘技能', f'遗忘技能{pokename}', '📖遗忘技能', action=2),
    ]
    if pokename == '伊布':
        buttons = [
            Button('📖学技能', f'学习技能{pokename}', '📖学技能', action=2),
            Button('📖遗忘技能', f'遗忘技能{pokename}', '📖遗忘技能', action=2),
        ]
    for jinhuainfo in jinhualist:
        buttons.append(
            Button(
                f'⏫进化{jinhuainfo[1]}',
                f'宝可梦进化{jinhuainfo[1]}',
                f'⏫进化{jinhuainfo[1]}',
                action=1,
            )
        )
    await bot.send_option(im, buttons)


@sv_pokemon_duel.on_fullmatch(('初始精灵列表', '初始宝可梦列表'))
async def get_chushi_list(bot, ev: Event):
    mes = []
    mes = ''
    mes += '可输入领取初始精灵+精灵名称领取'
    for bianhao in chushi_list:
        # img = CHAR_ICON_PATH / f'{POKEMON_LIST[bianhao][0]}.png'
        # img = await convert_img(img)
        mes += f'\n{CHARA_NAME[bianhao][0]} 属性:{POKEMON_LIST[bianhao][7]}'
    buttons = [
        Button('✅领取初始精灵', '领取初始精灵', '✅领取初始精灵', action=2),
    ]
    await bot.send_option(mes, buttons)


@sv_pokemon_duel.on_command(('领取初始精灵', '领取初始宝可梦'))
async def get_chushi_pokemon(bot, ev: Event):
    args = ev.text.split()
    if len(args) != 1:
        mes = '请输入 领取初始精灵+宝可梦名称。初始精灵列表可点击下方按钮查询'
        buttons = [
            Button('📖初始精灵列表', '初始精灵列表', '📖初始精灵列表', action=1),
        ]
        return await bot.send_option(mes, buttons)
    pokename = args[0]
    uid = ev.user_id

    my_pokemon = await POKE._get_pokemon_num(uid)
    if my_pokemon > 0:
        return await bot.send('您已经有精灵了，无法领取初始精灵。', at_sender=True)

    bianhao = await get_poke_bianhao(pokename)
    if bianhao == 0:
        return await bot.send('请输入正确的宝可梦名称。', at_sender=True)
    if bianhao not in chushi_list:
        return await bot.send(
            f'{POKEMON_LIST[bianhao][0]}不属于初始精灵，无法领取。',
            at_sender=True,
        )
    from ..utils.dbbase.storage import starter_transaction

    async with starter_transaction(uid):
        already_owned = await POKE._get_pokemon_num(uid) > 0
        if not already_owned:
            startype = await get_pokemon_star(uid)
            pokemon_info = await add_pokemon(uid, bianhao, startype)
            await POKE._add_pokemon_group(uid, bianhao)

            await POKE.update_pokemon_star(uid, bianhao, startype)
            if bianhao in [1,4,7]:
                go_didian = '1号道路'
            elif bianhao in [152,155,158]:
                go_didian = '29号道路'
            elif bianhao in [252,255,258]:
                go_didian = '101号道路'
            elif bianhao in [387,390,393]:
                go_didian = '201号道路'
            elif bianhao in [495,498,501]:
                go_didian = '合众19号道路'
            elif bianhao in [650,653,656]:
                go_didian = '卡洛斯2号道路'
            elif bianhao in [722,725,728]:
                go_didian = '阿罗拉1号道路'
            elif bianhao in [810,813,816]:
                go_didian = '伽勒尔1号道路'
            elif bianhao in [906,909,912]:
                go_didian = '南1区'
            else:
                csdidianlist = ['1号道路', '29号道路', '101号道路', '201号道路','合众19号道路','卡洛斯2号道路','阿罗拉1号道路','伽勒尔1号道路','南1区']
                go_didian = random.sample(csdidianlist, 1)[0]
            name = uid
            if ev.sender:
                sender = ev.sender
                if sender.get('nickname', '') != '':
                    name = sender['nickname']
            await POKE._new_map_info(uid, go_didian, name)
    if already_owned:
        return await bot.send('您已经有精灵了，无法领取初始精灵。', at_sender=True)

    HP, W_atk, W_def, M_atk, M_def, speed = await get_pokemon_shuxing(
        bianhao, pokemon_info
    )
    picfile = os.path.join(
        FILE_PATH, 'icon', f'{CHARA_NAME[bianhao][0]}.png'
    )
    mes = ''
    mes += '恭喜！您领取到了初始精灵\n'
    img = CHAR_ICON_PATH / f'{CHARA_NAME[bianhao][0]}.png'
    img = await convert_img(img)
    # mes.append(MessageSegment.image(img))
    mes += f'{starlist[startype]}{CHARA_NAME[bianhao][0]}\nLV:{pokemon_info[0]}\n属性:{POKEMON_LIST[bianhao][7]}\n性格:{pokemon_info[13]}\nHP:{HP}({pokemon_info[1]})\n物攻:{W_atk}({pokemon_info[2]})\n物防:{W_def}({pokemon_info[3]})\n特攻:{M_atk}({pokemon_info[4]})\n特防:{M_def}({pokemon_info[5]})\n速度:{speed}({pokemon_info[6]})\n'
    mes += f'可用技能\n{pokemon_info[14]}'
    buttons = [
        Button('📖精灵状态', f'精灵状态{pokename}', '📖精灵状态', action=1),
        Button('🏝️野外探索', '野外探索', '🏝️野外探索', action=1),
    ]
    await bot.send_option(mes, buttons)


@sv_pokemon_duel.on_fullmatch(['宝可梦重开'])
async def chongkai_pokemon(bot, ev: Event):
    uid = ev.user_id
    my_score = await SCORE.get_score(uid)
    mypropnum = await POKE._get_pokemon_prop(uid, '神奇糖果')
    if my_score < 0 or mypropnum < 0:
        return await bot.send('负债中，重开失败')
    await chongkai(uid)
    mes = '重开成功，请重新领取初始精灵开局'
    buttons = [
        Button('✅领取初始精灵', '领取初始精灵', '✅领取初始精灵', action=2),
    ]
    await bot.send_option(mes, buttons)


@sv_pokemon_duel.on_prefix(('放生精灵', '放生宝可梦'))
async def fangsheng_pokemon(bot, ev: Event):
    args = ev.text.split()
    if len(args) != 1:
        return await bot.send('请输入 放生精灵+宝可梦名称 中间用空格隔开。', at_sender=True)
    pokename = args[0]
    uid = ev.user_id
    bianhao = await get_poke_bianhao(pokename)
    if bianhao == 0:
        return await bot.send('请输入正确的宝可梦名称。', at_sender=True)
    pokemon_info = await get_pokeon_info(uid, bianhao)
    if pokemon_info == 0:
        return await bot.send(
            f'您还没有{CHARA_NAME[bianhao][0]}。', at_sender=True
        )

    my_pokemon = await POKE._get_pokemon_num(uid)
    if my_pokemon == 1:
        return await bot.send('您就这么一只精灵了，无法放生。', at_sender=True)
    await fangshen(uid, bianhao)
    startype = await POKE.get_pokemon_star(uid, bianhao)
    my_team = await POKE.get_pokemon_group(uid)
    pokemon_list = my_team.split(',')
    if str(bianhao) in pokemon_list:
        pokemon_list.remove(str(bianhao))
        pokemon_str = ','.join(pokemon_list)
        await POKE._add_pokemon_group(uid, pokemon_str)
    await bot.send(
        f'放生成功，{starlist[startype]}{CHARA_NAME[bianhao][0]}离你而去了',
        at_sender=True,
    )


@sv_pokemon_duel.on_prefix(('学习精灵技能', '学习宝可梦技能', '学习技能'))
async def add_pokemon_jineng(bot, ev: Event):
    args = ev.text.split()
    if len(args) != 2:
        return await bot.send(
            '请输入 学习精灵技能+宝可梦名称+技能名称 中间用空格隔开。',
            at_sender=True,
        )
    pokename = args[0]
    uid = ev.user_id
    bianhao = await get_poke_bianhao(pokename)
    if bianhao == 0:
        return await bot.send('请输入正确的宝可梦名称。', at_sender=True)
    pokemon_info = await get_pokeon_info(uid, bianhao)
    if pokemon_info == 0:
        return await bot.send(
            f'您还没有{CHARA_NAME[bianhao][0]}。', at_sender=True
        )
    jinengname = args[1]

    startype = await POKE.get_pokemon_star(uid, bianhao)
    myjinenglist = re.split(',', pokemon_info[14])
    if jinengname in myjinenglist:
        return await bot.send(
            f'学习失败，您的精灵 {starlist[startype]}{CHARA_NAME[bianhao][0]}已学会{jinengname}。',
            at_sender=True,
        )
    jinenglist = re.split(',', pokemon_info[14])
    if len(jinenglist) >= 4:
        return await bot.send(
            f'学习失败，您的精灵 {starlist[startype]}{CHARA_NAME[bianhao][0]}已学会4个技能，请先遗忘一个技能后再学习。',
            at_sender=True,
        )
    jinengzu = await get_level_jineng(pokemon_info[0], bianhao)
    xuexizu = POKEMON_XUEXI[bianhao]
    if jinengname not in jinengzu and jinengname not in xuexizu:
        return await bot.send(
            f'学习失败，当前等级学习无法学习该技能或{pokename}无法通过学习机学会该技能。',
            at_sender=True,
        )
    mes_xh = ''
    if jinengname not in jinengzu and jinengname in xuexizu:
        xuexiji_num = await POKE._get_pokemon_technical(uid, jinengname)
        if xuexiji_num == 0:
            return await bot.send(
                f'学习失败，您的[{jinengname}]技能机数量不足。',
                at_sender=True,
            )
        await POKE._add_pokemon_technical(uid,jinengname,-1)
        mes_xh = f'您消耗了招式学习机[{jinengname}]x1，使'

    jineng = pokemon_info[14] + ',' + jinengname

    await POKE._add_pokemon_jineng(uid, bianhao, jineng)
    mes = f'恭喜，{mes_xh}您的精灵 {starlist[startype]}{CHARA_NAME[bianhao][0]}学会了技能{jinengname}'
    buttons = [
        Button('📖学习技能', f'学习技能 {pokename}', '📖学习技能', action=2),
        Button('📖遗忘技能', f'遗忘技能 {pokename}', '📖遗忘技能', action=2),
        Button('📖精灵状态', f'精灵状态{pokename}', '📖精灵状态', action=1),
    ]
    await bot.send_option(mes, buttons)


@sv_pokemon_duel.on_prefix(('遗忘精灵技能', '遗忘宝可梦技能', '遗忘技能'))
async def del_pokemon_jineng(bot, ev: Event):
    args = ev.text.split()
    if len(args) != 2:
        return await bot.send(
            '请输入 学习精灵技能+宝可梦名称+技能名称 中间用空格隔开。',
            at_sender=True,
        )
    pokename = args[0]
    uid = ev.user_id
    bianhao = await get_poke_bianhao(pokename)
    if bianhao == 0:
        return await bot.send('请输入正确的宝可梦名称。', at_sender=True)
    pokemon_info = await get_pokeon_info(uid, bianhao)
    if pokemon_info == 0:
        return await bot.send(
            f'您还没有{CHARA_NAME[bianhao][0]}。', at_sender=True
        )
    jinengname = args[1]

    startype = await POKE.get_pokemon_star(uid, bianhao)
    if str(jinengname) not in str(pokemon_info[14]):
        return await bot.send(
            f'遗忘失败，您的精灵 {starlist[startype]}{CHARA_NAME[bianhao][0]}未学习{jinengname}。',
            at_sender=True,
        )
    jinenglist = re.split(',', pokemon_info[14])
    if len(jinenglist) == 1:
        return await bot.send('遗忘失败，需要保留1个技能用于对战哦。', at_sender=True)
    jinenglist.remove(jinengname)
    jineng = ''
    shul = 0
    for name in jinenglist:
        if shul > 0:
            jineng = jineng + ','
        jineng = jineng + name
        shul = shul + 1

    await POKE._add_pokemon_jineng(uid, bianhao, jineng)
    mes = f'成功，您的精灵{starlist[startype]}{CHARA_NAME[bianhao][0]}遗忘了技能{jinengname}'
    buttons = [
        Button('📖学习技能', f'学习技能 {pokename}', '📖学习技能', action=2),
        Button('📖遗忘技能', f'遗忘技能 {pokename}', '📖遗忘技能', action=2),
        Button('📖精灵状态', f'精灵状态{pokename}', '📖精灵状态', action=1),
    ]
    await bot.send_option(mes, buttons)


@sv_pokemon_duel.on_prefix(['精灵技能信息'])
async def get_jineng_info_text(bot, ev: Event):
    args = ev.text.split()
    if len(args) != 1:
        return await bot.send('请输入 精灵技能信息+技能名称 中间用空格隔开。', at_sender=True)
    jineng = args[0]
    try:
        jinenginfo = JINENG_LIST[jineng]
        mes = f'名称：{jineng}\n属性：{jinenginfo[0]}\n类型：{jinenginfo[1]}\n威力：{jinenginfo[2]}\n命中：{jinenginfo[3]}\nPP值：{jinenginfo[4]}\n描述：{jinenginfo[5]}'
        if jinenginfo[6] == '':
            mes += '\n技能未添加'
        else:
            mes += '\n技能已添加'
        await bot.send(mes)
    except:
        await bot.send('无法找到该技能，请输入正确的技能名称。', at_sender=True)


@sv_pokemon_duel.on_prefix(['宝可梦进化'])
async def get_jineng_info(bot, ev: Event):
    args = ev.text.split()
    if len(args) != 1:
        return await bot.send('请输入 宝可梦进化+宝可梦名称。', at_sender=True)
    pokename = args[0]
    uid = ev.user_id
    bianhao = await get_poke_bianhao(pokename)
    if bianhao == 0:
        return await bot.send('请输入正确的宝可梦名称。', at_sender=True)
    zhongzu = POKEMON_LIST[bianhao]
    if len(zhongzu) < 9:
        return await bot.send('暂时没有该宝可梦的进化信息，请等待后续更新。', at_sender=True)
    if zhongzu[8] == '-':
        return await bot.send('暂时没有该宝可梦的进化信息。', at_sender=True)
    use_flag = 0

    my_pokemon_list = await POKE._get_my_pokemon(uid)
    for pokemonid in my_pokemon_list:
        if int(pokemonid[0]) == int(bianhao):
            use_flag = 1
            break
    if use_flag == 1:
        return await bot.send(f'已经有{pokename}了，不能同时拥有同一只精灵哦。', at_sender=True)

    kid_poke_id = int(zhongzu[8])
    pokemon_info = await get_pokeon_info(uid, kid_poke_id)

    if pokemon_info == 0:
        return await bot.send(
            f'您还没有{CHARA_NAME[kid_poke_id][0]}，无法进化。',
            at_sender=True,
        )
    startype = await POKE.get_pokemon_star(uid, kid_poke_id)
    if zhongzu[9].isdigit():
        if pokemon_info[0] < int(zhongzu[9]):
            return await bot.send(
                f'进化成{CHARA_NAME[bianhao][0]}需要 Lv.{zhongzu[9]}\n您的{starlist[startype]}{CHARA_NAME[kid_poke_id][0]}等级为 Lv.{pokemon_info[0]}，无法进化',
                at_sender=True,
            )
        else:
            await POKE.update_pokemon_star(uid, bianhao, startype)
            await POKE._delete_poke_star_bianhao(uid, kid_poke_id)
            await POKE._add_pokemon_id(uid, kid_poke_id, bianhao)
            my_team = await POKE.get_pokemon_group(uid)
            pokemon_list = my_team.split(',')
            if str(kid_poke_id) in pokemon_list:
                team_list = []
                for pokeid in pokemon_list:
                    if int(pokeid) == int(kid_poke_id):
                        pokeid = bianhao
                    team_list.append(str(pokeid))
                pokemon_str = ','.join(team_list)
                await POKE._add_pokemon_group(uid, pokemon_str)
            mes = f'恭喜！您的宝可梦 {starlist[startype]}{CHARA_NAME[kid_poke_id][0]} 进化成了 {starlist[startype]}{CHARA_NAME[bianhao][0]}'
            buttons = [
                Button('📖学习技能', f'学习技能 {pokename}', '📖学习技能', action=2),
                Button('📖遗忘技能', f'遗忘技能 {pokename}', '📖遗忘技能', action=2),
                Button('📖精灵状态', f'精灵状态{pokename}', '📖精灵状态', action=1),
            ]
            await bot.send_option(mes, buttons)
    else:
        if zhongzu[9] == '-':
            return await bot.send(f'进化失败，进化成{CHARA_NAME[bianhao][0]}需要通过其他条件完成', at_sender=True)
        mypropnum = await POKE._get_pokemon_prop(uid, zhongzu[9])
        if mypropnum == 0:
            return await bot.send(
                f'进化成{CHARA_NAME[bianhao][0]}需要道具{zhongzu[9]}，您还没有该道具，无法进化',
                at_sender=True,
            )
        else:
            await POKE.update_pokemon_star(uid, bianhao, startype)
            await POKE._delete_poke_star_bianhao(uid, kid_poke_id)
            await POKE._add_pokemon_id(uid, kid_poke_id, bianhao)
            my_team = await POKE.get_pokemon_group(uid)
            pokemon_list = my_team.split(',')
            await POKE._add_pokemon_prop(uid, zhongzu[9], -1)
            if str(kid_poke_id) in pokemon_list:
                team_list = []
                for pokeid in pokemon_list:
                    if int(pokeid) == int(kid_poke_id):
                        pokeid = bianhao
                    team_list.append(str(pokeid))
                pokemon_str = ','.join(team_list)
                await POKE._add_pokemon_group(uid, pokemon_str)
            mes = f'恭喜！您的宝可梦 {starlist[startype]}{CHARA_NAME[kid_poke_id][0]} 进化成了 {starlist[startype]}{CHARA_NAME[bianhao][0]}'
            buttons = [
                Button('📖学习技能', f'学习技能 {pokename}', '📖学习技能', action=2),
                Button('📖遗忘技能', f'遗忘技能 {pokename}', '📖遗忘技能', action=2),
                Button('📖精灵状态', f'精灵状态{pokename}', '📖精灵状态', action=1),
            ]
            await bot.send_option(mes, buttons)


@sv_pokemon_duel.on_command(('我的精灵蛋', '我的宝可梦蛋'))
async def my_pokemon_egg_list(bot, ev: Event):
    page = ''.join(re.findall('^[a-zA-Z0-9_\u4e00-\u9fa5]+$', ev.text))
    if not page:
        page = 0
    else:
        page = int(page) - 1
    uid = ev.user_id

    myegglist = await POKE.get_pokemon_egg_list(uid, page)
    if myegglist == 0:
        return await bot.send('您还没有精灵蛋', at_sender=True)
    egg_num = await POKE.get_pokemon_egg_num(uid)
    page_num = math.floor(egg_num / 30) + 1
    mes = ''
    page = page + 1
    mes += f"<@{uid}>您的精灵蛋信息为(一页只显示30种按数量和编号排序):\n"
    for pokemoninfo in myegglist:
        mes += f'{CHARA_NAME[pokemoninfo[0]][0]} 数量 {pokemoninfo[1]}\n'
    if page_num > 1:
        mes += f'第({page}/{page_num})页'
    buttons = [
        Button('📖宝可梦孵化', '宝可梦孵化', '📖宝可梦孵化', action=2),
        Button('📖重置个体值', '重置个体值', '📖重置个体值', action=2),
        Button('📖丢弃精灵蛋', '丢弃精灵蛋', '📖丢弃精灵蛋', action=2),
    ]
    if page > 1:
        uppage = page - 1
        buttons.append(Button('⬅️上一页', f'我的精灵蛋{uppage}', '⬅️上一页', action=1))
    if page_num > 1:
        buttons.append(Button(f'⏺️跳转({page}/{page_num})', '我的精灵蛋', f'⏺️跳转({page}/{page_num})', action=2))
    if page < page_num:
        dowmpage = page + 1
        buttons.append(Button('➡️下一页', f'我的精灵蛋{dowmpage}', '➡️下一页', action=1))

    await bot.send_option(mes, buttons)


@sv_pokemon_duel.on_prefix(('丢弃精灵蛋', '丢弃宝可梦蛋'))
async def my_pokemon_egg_use(bot, ev: Event):
    args = ev.text.split()
    if len(args) < 1:
        return await bot.send('请输入 丢弃精灵蛋+宝可梦名称+丢弃数量。', at_sender=True)

    uid = ev.user_id
    pokename = args[0]
    uid = ev.user_id
    bianhao = await get_poke_bianhao(pokename)
    if bianhao == 0:
        return await bot.send('请输入正确的宝可梦名称。', at_sender=True)

    egg_num = await POKE.get_pokemon_egg(uid, bianhao)
    if egg_num == 0:
        return await bot.send(f'您还没有{pokename}的精灵蛋哦。', at_sender=True)
    if len(args) == 2:
        eggnum = int(args[1])
        if eggnum > egg_num:
            eggnum = egg_num
    else:
        eggnum = egg_num
    if eggnum < 1:
        return await bot.send('请输入正确的丢弃数量', at_sender=True)
    await POKE._add_pokemon_egg(uid, bianhao, 0 - eggnum)
    mes = f'成功！您丢弃了{pokename}精灵蛋x{eggnum}'
    buttons = [
        Button('📖宝可梦孵化', '宝可梦孵化', '📖宝可梦孵化', action=2),
        Button('📖重置个体值', '重置个体值', '📖重置个体值', action=2),
        Button('📖我的精灵蛋', '我的精灵蛋', '📖我的精灵蛋', action=1),
    ]
    await bot.send_option(mes, buttons)


@sv_pokemon_duel.on_command(('重置个体值', '个体值重置'))
async def my_pokemon_gt_up(bot, ev: Event):
    args = ev.text.split()
    if len(args) < 1:
        return await bot.send('请输入 重置个体值+宝可梦名称。', at_sender=True)
    pokename = args[0]
    uid = ev.user_id
    mapinfo = await POKE._get_map_now(uid)
    bianhao = await get_poke_bianhao(pokename)
    if bianhao == 0:
        return await bot.send('请输入正确的宝可梦名称。', at_sender=True)
    my_pokemon_info = await get_pokeon_info(uid, bianhao)
    if my_pokemon_info == 0:
        return await bot.send(
            f'您还没有{CHARA_NAME[bianhao][0]}。', at_sender=True
        )
    if len(args) > 1:
        rest_num = int(args[1])
    else:
        rest_num = 1
    
    if len(args) == 3:
        gt_max_num = int(args[2])
    else:
        gt_max_num = 3
    kidid = await get_pokemon_eggid(bianhao)
    egg_num = await POKE.get_pokemon_egg(uid, kidid)
    if egg_num == 0:
        return await bot.send(
            f'重置个体值需要消耗1枚同一种类型的精灵蛋哦，您没有{CHARA_NAME[kidid][0]}的精灵蛋。',
            at_sender=True,
        )
    (
        HP_o,
        W_atk_o,
        W_def_o,
        M_atk_o,
        M_def_o,
        speed_o,
    ) = await get_pokemon_shuxing(bianhao, my_pokemon_info)
    if egg_num < rest_num:
        return await bot.send(
            f'重置{rest_num}次个体值需要消耗{rest_num}枚同一种类型的精灵蛋哦，您的{CHARA_NAME[kidid][0]}精灵蛋不足。',
            at_sender=True,
        )
    if rest_num == 1:
        await POKE._add_pokemon_egg(uid, kidid, -1)
        startype = await POKE.get_pokemon_star(uid, bianhao)
        new_star_type = await get_pokemon_star(uid)
        if new_star_type > startype:
            startype = new_star_type
            await POKE.update_pokemon_star(uid, bianhao, startype)
        pokemon_info = await new_pokemon_gt(uid, bianhao, startype)

        HP, W_atk, W_def, M_atk, M_def, speed = await get_pokemon_shuxing(
            bianhao, pokemon_info
        )
        change_mes = f''
        if new_star_type > 0:
            change_mes = f'您的宝可梦形态好像发生了改变\n'
        mes = f'[{mapinfo[2]}]{change_mes}{starlist[startype]}{pokename}个体值重置成功，重置后属性如下\n'

        mes += f'HP:{HP_o}→{HP}({my_pokemon_info[1]}→{pokemon_info[1]})\n物攻:{W_atk_o}→{W_atk}({my_pokemon_info[2]}→{pokemon_info[2]})\n物防:{W_def_o}→{W_def}({my_pokemon_info[3]}→{pokemon_info[3]})\n特攻:{M_atk_o}→{M_atk}({my_pokemon_info[4]}→{pokemon_info[4]})\n特防:{M_def_o}→{M_def}({my_pokemon_info[5]}→{pokemon_info[5]})\n速度:{speed_o}→{speed}({my_pokemon_info[6]}→{pokemon_info[6]})'
        starflag = await POKE.get_pokemon_starrush(uid)
        mes += f'\n({starflag}/1024)'
        # mes.append(MessageSegment.image(img))

    else:
        startype = await POKE.get_pokemon_star(uid, bianhao)
        starflag = await POKE.get_pokemon_starrush(uid)
        jishu = 0
        rest_flag = 0
        while rest_num > 0 and rest_flag == 0:
            starflag += 1
            jishu += 1
            rest_num = rest_num - 1
            star_num = int(math.floor(random.uniform(0, 40960)))
            new_star_type = 0
            if starflag >= 1024 or star_num <= 10:
                new_star_type = 1
                star_num2 = int(math.floor(random.uniform(0, 160)))
                print(star_num2)
                if star_num2 <= 10:
                    new_star_type = 2
            if starflag == 1023:
                rest_flag = 1
            if new_star_type > 0:
                starflag = 0
                rest_flag = 2
            if new_star_type > startype:
                startype = new_star_type
                await POKE.update_pokemon_star(uid, bianhao, startype)
            pokemon_info = []
            pokemon_info.append(my_pokemon_info[0])
            gtmax = []
            if startype > 0:
                gtmax = random.sample([1, 2, 3, 4, 5, 6], startype)
            if bianhao in jinyonglist:
                gtmax = random.sample([1, 2, 3, 4, 5, 6], 3)
            gt_max_sl = 0
            for num in range(1, 7):
                if num in gtmax:
                    gt_num = 31
                else:
                    gt_num = int(math.floor(random.uniform(1, 32)))
                pokemon_info.append(gt_num)
                if gt_num == 31:
                    gt_max_sl += 1
            if gt_max_sl >= gt_max_num:
                rest_flag = 3
            for num in range(7, 17):
                pokemon_info.append(my_pokemon_info[num])
        await POKE.update_pokemon_starrush(uid, jishu)
        if rest_flag == 0:
            mes = f'[{mapinfo[2]}]您的个体值{jishu}次重置完成，重置后属性如下'
        if rest_flag == 1:
            mes = f'[{mapinfo[2]}]您的个体值{jishu}次重置成功，还差一次就出闪光啦，重置后属性如下'
        if rest_flag == 2:
            mes = f'[{mapinfo[2]}]您的个体值{jishu}次重置成功，您的精灵形象发生了改变，重置后属性如下'
            await POKE.new_pokemon_starrush(uid)
        if rest_flag == 3:
            mes = f'[{mapinfo[2]}]您的个体值{jishu}次重置成功，您的精灵拥有了很高的潜力，重置后属性如下'
        await POKE._add_pokemon_egg(uid, kidid, 0 - jishu)
        await POKE._add_pokemon_info(uid, bianhao, pokemon_info, my_pokemon_info[15])
        HP, W_atk, W_def, M_atk, M_def, speed = await get_pokemon_shuxing(
            bianhao, pokemon_info
        )
        mes += f'\n{starlist[startype]}{pokename}\n'
        mes += f'HP:{HP_o}→{HP}({my_pokemon_info[1]}→{pokemon_info[1]})\n物攻:{W_atk_o}→{W_atk}({my_pokemon_info[2]}→{pokemon_info[2]})\n物防:{W_def_o}→{W_def}({my_pokemon_info[3]}→{pokemon_info[3]})\n特攻:{M_atk_o}→{M_atk}({my_pokemon_info[4]}→{pokemon_info[4]})\n特防:{M_def_o}→{M_def}({my_pokemon_info[5]}→{pokemon_info[5]})\n速度:{speed_o}→{speed}({my_pokemon_info[6]}→{pokemon_info[6]})'
        mes += f'\n({starflag}/1024)'
    buttons = [
        Button('📖精灵状态', f'精灵状态{pokename}', '📖精灵状态', action=1),
        Button('📖重置个体值', f'重置个体值{pokename}', '📖重置个体值', action=2),
    ]
    await bot.send_option(mes, buttons)


@sv_pokemon_duel.on_command(['宝可梦重生'])
async def get_pokemon_form_chongsheng(bot, ev: Event):
    args = ev.text.split()
    if len(args) != 1:
        return await bot.send('请输入 宝可梦重生+宝可梦名称。', at_sender=True)
    pokename = args[0]
    uid = ev.user_id
    bianhao = await get_poke_bianhao(pokename)
    if bianhao == 0:
        return await bot.send('请输入正确的宝可梦名称。', at_sender=True)

    my_pokemon_info = await get_pokeon_info(uid, bianhao)
    if my_pokemon_info == 0:
        return await bot.send(
            f'您还没有{CHARA_NAME[bianhao][0]}。', at_sender=True
        )
    if my_pokemon_info[0] < 100:
        return await bot.send(f'您的{pokename}等级不足100，无法重生。', at_sender=True)

    my_pokemon = await POKE._get_pokemon_num(uid)
    if my_pokemon == 1:
        return await bot.send('您就这么一只精灵了，无法重生。', at_sender=True)

    eggid = await get_pokemon_eggid(bianhao)
    await fangshen(uid, bianhao)
    my_team = await POKE.get_pokemon_group(uid)
    pokemon_list = my_team.split(',')
    if str(bianhao) in pokemon_list:
        pokemon_list.remove(str(bianhao))
        pokemon_str = ','.join(pokemon_list)
        await POKE._add_pokemon_group(uid, pokemon_str)
    if eggid == 10:
        chongsheng_num = await POKE.get_chongsheng_num(uid,384)
        if chongsheng_num >= 233:
            eggid = 384
            await POKE._new_chongsheng_num(uid,384)
        else:
            await POKE.update_chongsheng(uid,384,1)
    await POKE._add_pokemon_egg(uid, eggid, 1)
    mes = f'{pokename}重生成功，您获得了{CHARA_NAME[eggid][0]}精灵蛋x1'
    buttons = [
        Button('📖宝可梦孵化', f'宝可梦孵化{CHARA_NAME[eggid][0]}', '📖宝可梦孵化', action=1),
    ]
    await bot.send_option(mes, buttons)


@sv_pokemon_duel.on_command(['赠送物品'])
async def give_prop_pokemon_egg(bot, ev: Event):
    args = ev.text.split()
    uid = ev.user_id
    if len(args) < 2:
        return await bot.send('请输入 赠送物品[道具/精灵蛋/金币/学习机][名称][数量][赠送对象昵称/at]。', at_sender=True)
    proptype = args[0]
    if proptype not in ['金币','金钱','道具', '精灵蛋', '宝可梦蛋', '蛋', '学习机']:
        return await bot.send('请输入正确的类型 道具/精灵蛋/金币/学习机。', at_sender=True)
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
                return await bot.send('请输入正确的指令 赠送物品[金币/金钱][数量][昵称/at]。', at_sender=True)
            snickname = args[2]
        else:
            if len(args) < 4:
                return await bot.send('请输入正确的指令 赠送物品[道具/精灵蛋/学习机][名称][数量][昵称/at]。',at_sender=True)
            snickname = args[3]
        smapinfo = await POKE._get_map_info_nickname(snickname)
        if smapinfo[2] == 0:
            return await bot.send(
                '没有找到该训练家，请输入 正确的训练家昵称或at该名训练家。',
                at_sender=True,
            )
        suid = smapinfo[2]
        sname = snickname
    
    propname = args[1]
    if len(args) >= 3 and proptype in ['道具', '精灵蛋', '宝可梦蛋', '蛋', '学习机']:
        if args[2].isdigit():
            propnum = int(args[2])
        else:
            propnum = 1
    else:
        propnum = 1
    if propnum < 1:
        return await bot.send('赠送物品的数量需大于0。', at_sender=True)
    break_flag = 0
    if suid == '34674183F5CFA2481E4249C32A3B54B5':
        break_flag = 1
    if proptype == '金币' or proptype == '金钱':
        propnum = int(args[1])
        if propnum < 1:
            return await bot.send('赠送金币的数量需大于1。', at_sender=True)
        my_score = await SCORE.get_score(uid)
        if break_flag == 0:
            if my_score < propnum:
                return await bot.send('您的金币不足',at_sender=True)
            await SCORE.update_score(uid, 0 - propnum)
        await SCORE.update_score(suid, propnum)
        mes = f'您赠送给了{sname} 金币x{propnum}。'
    if proptype == '道具':
        propkeylist = proplist.keys()
        if propname not in propkeylist:
            return await bot.send('无法找到该道具，请输入正确的道具名称。', at_sender=True)
        mypropnum = await POKE._get_pokemon_prop(uid, propname)
        if break_flag == 0:
            if mypropnum == 0:
                return await bot.send(f'您还没有{propname}哦。', at_sender=True)
            if mypropnum < propnum:
                return await bot.send(
                    f'您的{propname}数量小于{propnum}，赠送失败。', at_sender=True
                )
            await POKE._add_pokemon_prop(uid, propname, 0 - propnum)
        await POKE._add_pokemon_prop(suid, propname, propnum)
        mes = f'您赠送给了{sname} 道具{propname}x{propnum}。'
    if proptype == '学习机':
        jinenglist = JINENG_LIST.keys()
        if propname not in jinenglist:
            return await bot.send('无法找到该技能，请输入正确的技能学习机名称。', at_sender=True)
        xuexiji_num = await POKE._get_pokemon_technical(uid, propname)
        if break_flag == 0:
            if xuexiji_num == 0:
                return await bot.send(f'您还没有{propname}学习机哦。', at_sender=True)
            if xuexiji_num < propnum:
                return await bot.send(
                    f'您的{propname}学习机数量小于{propnum}，赠送失败。', at_sender=True
                )
            await POKE._add_pokemon_technical(uid,propname,0 - propnum)
        await POKE._add_pokemon_technical(suid,propname,propnum)
        mes = f'您赠送给了{sname} 学习机{propname}x{propnum}。'
    if proptype == '精灵蛋' or proptype == '宝可梦蛋' or proptype == '蛋':
        proptype = '精灵蛋'
        bianhao = await get_poke_bianhao(propname)
        if bianhao == 0:
            return await bot.send('请输入正确的宝可梦名称。', at_sender=True)
        egg_num = await POKE.get_pokemon_egg(uid, bianhao)
        if break_flag == 0:
            if egg_num == 0:
                return await bot.send(f'您还没有{propname}的精灵蛋哦。', at_sender=True)
            if egg_num < propnum:
                return await bot.send(
                    f'您的{propname}精灵蛋数量小于{propnum}，赠送失败。', at_sender=True
                )

            await POKE._add_pokemon_egg(uid, bianhao, 0 - propnum)
        await POKE._add_pokemon_egg(suid, bianhao, propnum)
        mes = f'您赠送给了{sname} {propname}精灵蛋x{propnum}。'
    await bot.send(mes)


@sv_pokemon_duel.on_prefix(['宝可梦孵化'])
async def get_pokemon_form_egg(bot, ev: Event):
    args = ev.text.split()
    if len(args) != 1:
        return await bot.send('请输入 宝可梦孵化+宝可梦名称。', at_sender=True)
    pokename = args[0]
    uid = ev.user_id
    bianhao = await get_poke_bianhao(pokename)
    if bianhao == 0:
        return await bot.send('请输入正确的宝可梦名称。', at_sender=True)

    egg_num = await POKE.get_pokemon_egg(uid, bianhao)
    if egg_num == 0:
        return await bot.send(f'您还没有{pokename}的精灵蛋哦。', at_sender=True)
    use_flag = 0
    my_pokemon_list = await POKE._get_my_pokemon(uid)
    for pokemonid in my_pokemon_list:
        if int(pokemonid[0]) == int(bianhao):
            use_flag = 1
            break
    if use_flag == 1:
        return await bot.send(f'已经有{pokename}了，不能同时拥有同一只精灵哦。', at_sender=True)
    await POKE._add_pokemon_egg(uid, bianhao, -1)

    startype = await get_pokemon_star(uid)
    pokemon_info = await add_pokemon(uid, bianhao, startype)
    await POKE.update_pokemon_star(uid, bianhao, startype)
    HP, W_atk, W_def, M_atk, M_def, speed = await get_pokemon_shuxing(
        bianhao, pokemon_info
    )
    mes = ''
    mes += '恭喜!孵化成功了\n'
    mes += f'{starlist[startype]}{POKEMON_LIST[bianhao][0]}\nLV:{pokemon_info[0]}\n属性:{POKEMON_LIST[bianhao][7]}\n性格:{pokemon_info[13]}\nHP:{HP}({pokemon_info[1]})\n物攻:{W_atk}({pokemon_info[2]})\n物防:{W_def}({pokemon_info[3]})\n特攻:{M_atk}({pokemon_info[4]})\n特防:{M_def}({pokemon_info[5]})\n速度:{speed}({pokemon_info[6]})\n'
    mes += f'可用技能\n{pokemon_info[14]}'
    my_team = await POKE.get_pokemon_group(uid)
    pokemon_list = my_team.split(',')
    if len(pokemon_list) < 4:
        pokemon_list.append(str(bianhao))
        pokemon_str = ','.join(pokemon_list)
        await POKE._add_pokemon_group(uid, pokemon_str)
    img = CHAR_ICON_PATH / f'{CHARA_NAME[bianhao][0]}.png'
    img = await convert_img(img)
    mesg = []
    mesg.append(MessageSegment.text(mes))
    mesg.append(MessageSegment.image(img))
    buttons = [
        Button('📖精灵状态', f'精灵状态{pokename}', '📖精灵状态', action=1),
        Button('📖重置个体值', f'重置个体值{pokename}', '📖重置个体值', action=1),
    ]
    await bot.send_option(mesg, buttons)

@sv_pokemon_duel.on_fullmatch(['形态列表'])
async def get_pokemon_xingtai_list(bot, ev: Event):
    mes = '下面为宝可梦可转换的形态:'
    for pokemonid in CHARA_NAME:
        if pokemonid > 10000:
            xingtai_type = int(str(pokemonid)[-3:])
            if xingtai_type < 500:
                fpokemonid = int(str(pokemonid)[0:-3])
                pokename2 = CHARA_NAME[pokemonid][0]
                if ')' in pokename2:
                    pokename2 = pokename.replace(')','）')
                mes += f"\n{CHARA_NAME[fpokemonid][0]}可转换为{CHARA_NAME[pokemonid][0]}"
    buttons = [
        Button('🔄形态转换', '形态转换', '🔄形态转换', action=2),
        Button('🔍︎查看图鉴', '精灵图鉴', '🔍︎查看图鉴', action=2),
    ]
    await bot.send_option(mes, buttons)

@sv_pokemon_duel.on_prefix(['形态转换'])
async def get_pokemon_form_xingtai(bot, ev: Event):
    args = ev.text.split()
    if len(args) != 2:
        return await bot.send('请输入 形态转换[转换前的形态名称][转换后的形态名称]\n如形态转换 喵喵 喵喵(阿罗拉)。', at_sender=True)
    oldpokename = args[0]
    newpokename = args[1]
    uid = ev.user_id
    oldbianhao = await get_poke_bianhao(oldpokename)
    newbianhao = await get_poke_bianhao(newpokename)
    if oldbianhao == 0 or newbianhao == 0:
        return await bot.send('请输入正确的宝可梦名称。', at_sender=True)
    my_pokemon_info = await get_pokeon_info(uid, oldbianhao)
    if my_pokemon_info == 0:
        return await bot.send(
            f'您还没有{CHARA_NAME[oldbianhao][0]}。', at_sender=True
        )
    foldbianhao = oldbianhao
    xingtai_type = 0
    if foldbianhao > 10000:
        xingtai_type = int(str(foldbianhao)[-3:])
        foldbianhao = str(foldbianhao)[0:-3]
    fnewbianhao = newbianhao
    if fnewbianhao > 10000:
        xingtai_type = int(str(fnewbianhao)[-3:])
        fnewbianhao = str(fnewbianhao)[0:-3]
    if xingtai_type > 500:
        return await bot.send(f'转换失败！', at_sender=True)
    if str(fnewbianhao) != str(foldbianhao):
        return await bot.send(f'转换失败！不同类型的宝可梦形态无法转换。', at_sender=True)
    pokemon_info = await POKE._get_pokemon_info(uid, newbianhao)
    if pokemon_info == 0:
        my_score = await SCORE.get_score(uid)
        if my_score < 50000:
            return await bot.send('转换形态需要金币50000,您的金币不足',at_sender=True)
        await SCORE.update_score(uid, -50000)
        startype = await POKE.get_pokemon_star(uid, oldbianhao)
        await POKE.update_pokemon_star(uid, newbianhao, startype)
        await POKE._delete_poke_star_bianhao(uid, oldbianhao)
        await POKE._add_pokemon_id(uid, oldbianhao, newbianhao)
        my_team = await POKE.get_pokemon_group(uid)
        pokemon_list = my_team.split(',')
        if str(oldbianhao) in pokemon_list:
            team_list = []
            for pokeid in pokemon_list:
                if int(pokeid) == int(oldbianhao):
                    pokeid = newbianhao
                team_list.append(str(pokeid))
            pokemon_str = ','.join(team_list)
            await POKE._add_pokemon_group(uid, pokemon_str)
        mes = f'您消耗了50000金币,您的{oldpokename}变成了{newpokename}'
        buttons = [
            Button('📖精灵状态', f'精灵状态{newpokename}', '📖精灵状态', action=1),
            Button('📖查看图鉴', f'精灵图鉴{newpokename}', '📖查看图鉴', action=1),
        ]
        await bot.send_option(mes, buttons)
    else:
        return await bot.send(f"您已经有{newpokename}，同一只精灵无法持有2只及以上哦")


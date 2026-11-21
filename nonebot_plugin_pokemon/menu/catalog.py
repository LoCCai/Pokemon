"""指令目录（菜单 / LLM 发现 / 网页指令面板的单一事实来源）。

* 每个已注册的 gsuid 触发器都会映射到一条目录项；
* 菜单（PicMenu Next 外部菜单与 ``PluginMetadata.extra.menu_data``）由这里生成；
* MoEllmChats 与 QWeb 工具桥读取同一份数据，避免"菜单能点、AI 不知道"的漂移。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from ..compat.sv import SV, list_commands

CATEGORY_ORDER = ["基础", "养成", "探索", "对战", "道具", "小游戏", "排行", "管理", "资源", "网页"]


@dataclass
class CatalogEntry:
    func: str
    category: str
    brief: str
    detail: str
    intents: List[str] = field(default_factory=list)
    hidden: bool = False
    permission: str = ""
    aliases: List[str] = field(default_factory=list)


C = CatalogEntry

# key = 处理函数短名（module.function）
CATALOG: Dict[str, CatalogEntry] = {
    # ---------------------------------------------------------------- 基础
    "pokemon_duel.pokemon_help": C(
        "宝可梦帮助", "基础", "查看宝可梦游戏的主指令列表与新手开局说明。",
        "发送 `宝可梦帮助` 或 `精灵帮助`。首次游玩请先发送 `领取初始精灵 小火龙` 之类的指令开局。",
        ["宝可梦怎么玩", "这个宝可梦游戏有哪些指令", "宝可梦新手帮助"],
    ),
    "pokemon_duel.pokemon_gonggao": C(
        "更新公告", "基础", "查看宝可梦插件最近的更新内容。",
        "发送 `更新公告` 或 `查看公告`。", ["宝可梦更新了什么", "查看宝可梦公告"],
    ),
    "pokemon_duel.pokemon_help_game": C(
        "小游戏帮助", "小游戏", "查看猜图鉴、猜技能、猜属性、猜精灵、我是谁等小游戏玩法。",
        "发送 `小游戏帮助` 或 `宝可梦小游戏帮助`。", ["宝可梦小游戏怎么玩", "有哪些宝可梦小游戏"],
    ),
    "pokemon_duel.get_my_qqgroup_id": C(
        "查询虚拟ID", "基础", "查看当前群聊与用户的虚拟 ID，便于数据转移和排查。",
        "发送 `wsid` 或 `虚拟id`。", ["查看我的虚拟id", "查询群虚拟id"], hidden=True,
    ),
    "pokemon_duel.get_jineng_use_text": C(
        "技能测试", "基础", "让指定宝可梦对测试木桩使用一次技能，查看伤害与效果。",
        "发送 `技能测试 宝可梦名 技能名`，例如 `技能测试 皮卡丘 十万伏特`。",
        ["测试宝可梦技能伤害", "用皮卡丘放十万伏特试试"],
    ),
    # ---------------------------------------------------------------- 养成
    "pokemon_duel.my_pokemon_list": C(
        "我的精灵列表", "养成", "分页查看自己拥有的宝可梦、等级与闪光标记。",
        "发送 `我的精灵列表` 或 `我的宝可梦列表`，可在指令后跟页码，例如 `我的精灵列表2`。",
        ["看看我有哪些宝可梦", "列出我的精灵", "我的宝可梦等级"],
    ),
    "pokemon_duel.show_poke_info": C(
        "精灵图鉴", "养成", "查询一只宝可梦的图鉴：属性、种族值、进化链、可学技能与图鉴描述。",
        "发送 `精灵图鉴 宝可梦名`，例如 `精灵图鉴 皮卡丘`。",
        ["查一下皮卡丘的图鉴", "宝可梦图鉴", "这只宝可梦能学什么技能"],
    ),
    "pokemon_duel.show_poke_info_star": C(
        "闪光图鉴", "养成", "查看宝可梦的闪光形态图鉴与进化链。",
        "发送 `闪光图鉴 宝可梦名` 或 `闪光宝可梦图鉴 宝可梦名`。",
        ["查看闪光皮卡丘", "闪光宝可梦图鉴"],
    ),
    "pokemon_duel.get_my_poke_info_t": C(
        "精灵状态", "养成", "查看自己某只宝可梦的等级、性格、个体值、努力值、技能与进化信息。",
        "发送 `精灵状态 宝可梦名`，例如 `精灵状态 皮卡丘`。",
        ["看看我的皮卡丘状态", "我的宝可梦属性", "查询精灵个体值"],
    ),
    "pokemon_duel.get_chushi_list": C(
        "初始精灵列表", "养成", "列出可以领取的御三家初始宝可梦及属性。",
        "发送 `初始精灵列表` 或 `初始宝可梦列表`。", ["有哪些初始宝可梦", "御三家列表"],
    ),
    "pokemon_duel.get_chushi_pokemon": C(
        "领取初始精灵", "养成", "领取一只御三家作为初始宝可梦并开启地图。",
        "发送 `领取初始精灵 宝可梦名`，例如 `领取初始精灵 小火龙`。已有宝可梦时不能重复领取。",
        ["帮我领取小火龙", "我要初始宝可梦", "开局领一只皮卡丘"],
    ),
    "pokemon_duel.chongkai_pokemon": C(
        "宝可梦重开", "养成", "清空当前存档并重新领取初始精灵；负债时不可重开。",
        "发送 `宝可梦重开`。", ["重置宝可梦存档", "我想重新开始宝可梦"],
    ),
    "pokemon_duel.fangsheng_pokemon": C(
        "放生精灵", "养成", "放生一只自己拥有的宝可梦。",
        "发送 `放生精灵 宝可梦名` 或 `放生宝可梦 宝可梦名`。", ["放生这只宝可梦", "不要这只精灵了"],
    ),
    "pokemon_duel.add_pokemon_jineng": C(
        "学习技能", "养成", "让宝可梦学习一个可学技能。",
        "发送 `学习技能 宝可梦名 技能名`，例如 `学习技能 皮卡丘 十万伏特`。",
        ["让皮卡丘学十万伏特", "学习宝可梦技能"],
    ),
    "pokemon_duel.del_pokemon_jineng": C(
        "遗忘技能", "养成", "让宝可梦遗忘一个已学技能。",
        "发送 `遗忘技能 宝可梦名 技能名`。", ["让皮卡丘忘掉技能", "遗忘宝可梦技能"],
    ),
    "pokemon_duel.get_jineng_info_text": C(
        "技能信息", "养成", "查询一个技能的类型、威力、命中、PP 与效果说明。",
        "发送 `技能信息 技能名`，例如 `技能信息 十万伏特`。", ["十万伏特是什么技能", "查询技能效果"],
    ),
    "pokemon_duel.get_jineng_info": C(
        "宝可梦技能", "养成", "查看某只宝可梦在当前等级可学习/已学会的技能列表。",
        "发送 `宝可梦技能 宝可梦名`。", ["皮卡丘会哪些技能", "查看宝可梦技能表"],
    ),
    "pokemon_duel.my_pokemon_egg_list": C(
        "我的精灵蛋", "养成", "查看自己持有的精灵蛋与数量。",
        "发送 `我的精灵蛋` 或 `我的宝可梦蛋`。", ["看看我的精灵蛋", "我有多少宝可梦蛋"],
    ),
    "pokemon_duel.my_pokemon_egg_use": C(
        "丢弃精灵蛋", "养成", "丢弃指定宝可梦的精灵蛋。",
        "发送 `丢弃精灵蛋 宝可梦名`。", ["丢掉这个精灵蛋"],
    ),
    "pokemon_duel.my_pokemon_gt_up": C(
        "重置个体值", "养成", "消耗初始形态精灵蛋重置宝可梦个体值，可指定次数。",
        "发送 `重置个体值 宝可梦名`，后面可跟数量，例如 `重置个体值 皮卡丘 3`。",
        ["洗个体值", "重置皮卡丘个体值"],
    ),
    "pokemon_duel.get_pokemon_form_chongsheng": C(
        "宝可梦重生", "养成", "让 100 级宝可梦重生为精灵蛋。",
        "发送 `宝可梦重生 宝可梦名`。", ["把满级宝可梦变回蛋", "宝可梦重生"],
    ),
    "pokemon_duel.give_prop_pokemon_egg": C(
        "赠送物品", "养成", "把道具赠送给其他训练家（可 @ 对方）。",
        "发送 `赠送物品 @对方 道具名 数量`。", ["送道具给好友", "赠送宝可梦道具"],
    ),
    "pokemon_duel.get_pokemon_form_egg": C(
        "宝可梦孵化", "养成", "消耗对应精灵蛋孵化一只 5 级宝可梦。",
        "发送 `宝可梦孵化 宝可梦名`。", ["孵化精灵蛋", "把蛋孵出来"],
    ),
    "pokemon_duel.get_pokemon_xingtai_list": C(
        "形态列表", "养成", "查看支持形态转换的宝可梦列表。",
        "发送 `形态列表`。", ["有哪些宝可梦形态", "查看形态转换列表"],
    ),
    "pokemon_duel.get_pokemon_form_xingtai": C(
        "形态转换", "养成", "在宝可梦的不同形态之间转换。",
        "发送 `形态转换 宝可梦名 形态名`。", ["切换宝可梦形态", "让宝可梦变成另一个形态"],
    ),
    # ---------------------------------------------------------------- 探索
    "map.map_ts_test_noauto_use": C(
        "野外探索", "探索", "在当前地点探索，遭遇野生宝可梦或训练家并获得经验；有内置 5 秒 CD。",
        "发送 `野外探索`。可用 `开启自动探索` / `结束自动探索` 托管。",
        ["去野外探索", "遇一只野生宝可梦", "野外刷经验"],
    ),
    "map.map_ts_test_noauto_use_chuidiao": C(
        "野外垂钓", "探索", "在当前水域垂钓，遭遇水系宝可梦。",
        "发送 `野外垂钓`。", ["钓鱼", "在水边钓宝可梦"],
    ),
    "map.map_ts_auto_start": C(
        "开启自动探索", "探索", "开启野外自动探索，按固定间隔自动遭遇。",
        "发送 `开启自动探索`。", ["自动刷野", "开启自动探索"],
    ),
    "map.map_ts_auto_end": C(
        "结束自动探索", "探索", "关闭野外自动探索。",
        "发送 `结束自动探索` 或 `关闭自动探索`。", ["停止自动探索", "关掉自动刷野"],
    ),
    "map.map_info_now": C(
        "当前地点信息", "探索", "查看当前所在地点、地区与可遇宝可梦。",
        "发送 `当前地点信息`。", ["我现在在哪", "当前地图地点"],
    ),
    "map.show_map_info_now": C(
        "查看地图", "探索", "查看关东/成都/丰缘/神奥/合众/卡洛斯/阿罗拉/伽勒尔/帕底亚地图与地点。",
        "发送 `查看地图关东` 等，地区名可省略则查看当前地区。",
        ["看看关东地图", "宝可梦地图", "有哪些地点可以去"],
    ),
    "map.pokemom_go_map": C(
        "前往", "探索", "前往指定地点。",
        "发送 `前往 地点名`，例如 `前往 1号道路`。", ["去1号道路", "移动到下一个地点"],
    ),
    "map.pokemom_map_info_have": C(
        "分布查询", "探索", "查询某只宝可梦在哪些地区/地点分布。",
        "发送 `分布查询 宝可梦名` 或 `精灵分布 宝可梦名`。", ["皮卡丘在哪里抓", "宝可梦分布"],
    ),
    "map.pokemom_new_map": C(
        "选择初始地区", "探索", "重新选择初始地区。",
        "发送 `选择初始地区 地区名`。", ["选择关东地区", "换初始地区"],
    ),
    "map.map_my_info": C(
        "训练家名片", "探索", "生成训练家名片，展示昵称、称号、金钱、声望与队伍。",
        "发送 `训练家名片`。", ["看看我的训练家资料", "生成训练家名片"],
    ),
    "map.map_my_score": C(
        "我的金钱", "探索", "查看自己的金钱与声望。",
        "发送 `我的金钱`。", ["我有多少钱", "查看金币"],
    ),
    "map.map_work_test": C(
        "打工", "探索", "在城镇打工赚取金币，有每日次数限制。",
        "发送 `打工`。", ["去打工赚钱", "赚点金币"],
    ),
    "map.update_my_name": C(
        "修改训练家名称", "探索", "修改训练家昵称；昵称唯一，作为对战识别符。",
        "发送 `修改训练家名称 新昵称`，例如 `修改训练家名称 小智`。",
        ["把我的名字改成小智", "修改训练家昵称"],
    ),
    "map.show_poke_info": C(
        "替换消息发送方式", "管理", "切换游戏消息以图片还是文本方式发送。",
        "发送 `替换消息发送方式 图片|文本`。", ["把宝可梦消息改成图片", "切换消息发送方式"], hidden=True,
    ),
    "map.pokemon_pk_auto": C(
        "训练家对战", "对战", "向指定训练家发起对战，可指定其昵称或 @ 对方。",
        "发送 `训练家对战 昵称`（可 @ 对方）。", ["和这个训练家打一场", "挑战训练家"],
    ),
    "map.map_my_group": C(
        "更新队伍", "对战", "设置出战队伍，最多 4 只，用空格分隔。",
        "发送 `更新队伍 宝可梦名1 宝可梦名2 ...`。", ["设置出战队伍", "把皮卡丘放进队伍"],
    ),
    "map.get_day_pokemon_refresh": C(
        "大量出现信息", "探索", "查看当前各地区大量出现的宝可梦。",
        "发送 `大量出现信息`。", ["今天哪里大量出现", "查看大量出现"],
    ),
    "map.new_refresh_send_group": C(
        "标记消息推送", "探索", "把当前群/私聊标记为大量出现信息推送目标。",
        "发送 `标记消息推送`。", ["这个群接收大量出现推送"],
    ),
    "map.del_refresh_send_group": C(
        "清除消息推送", "探索", "取消当前群/私聊的大量出现推送。",
        "发送 `清除消息推送`。", ["取消大量出现推送"],
    ),
    "map.get_day_pokemon_refresh_send": C(
        "大量出现信息推送", "探索", "立即向已标记的群推送一次大量出现信息。",
        "发送 `大量出现信息推送`。", ["推送大量出现", "发一次大量出现"],
    ),
    # ---------------------------------------------------------------- 对战
    "fight.fight_help": C(
        "战斗帮助", "对战", "查看道馆、天王、首领、试炼塔、匹配对战等战斗玩法说明。",
        "发送 `战斗帮助`。", ["宝可梦怎么战斗", "对战玩法帮助"],
    ),
    "fight.pk_vs_daoguan": C(
        "挑战道馆", "对战", "挑战当前地区道馆馆主。",
        "发送 `挑战道馆`。", ["打道馆", "挑战馆主"],
    ),
    "fight.pk_vs_tianwang": C(
        "挑战天王", "对战", "挑战四天王。",
        "发送 `挑战天王`。", ["打四大天王", "挑战天王"],
    ),
    "fight.pk_vs_guanjun": C(
        "挑战四天王冠军", "对战", "挑战地区冠军。",
        "发送 `挑战四天王冠军`。", ["打冠军", "挑战联盟冠军"],
    ),
    "fight.pokemon_pk_wjb": C(
        "无级别对战", "对战", "与其他训练家进行无级别匹配对战，可 @ 对手。",
        "发送 `无级别对战`（可 @ 对手）。", ["来一场无级别对战", "随便打一场"],
    ),
    "fight.pokemon_pk_xzdj": C(
        "限制级对战", "对战", "进行有等级限制的匹配对战。",
        "发送 `限制级对战 等级`（可 @ 对手）。", ["限制级对战50级", "来一场限制级对战"],
    ),
    "fight.pokemon_pk_boss_list": C(
        "首领列表", "对战", "查看当前可挑战的首领。",
        "发送 `首领列表` 或 `boss列表`。", ["有哪些boss", "查看首领"],
    ),
    "fight.pokemon_pk_boss_week_info": C(
        "首领信息", "对战", "查看周本首领的属性、等级与奖励。",
        "发送 `首领信息` 或 `周本boss信息`。", ["本周boss是什么", "查看周本首领"],
    ),
    "fight.pokemon_pk_boss_week": C(
        "首领挑战", "对战", "挑战周本首领，按伤害结算奖励。",
        "发送 `首领挑战` 或 `周本boss挑战`。", ["打周本boss", "挑战本周首领"],
    ),
    "fight.pokemon_pk_boss_sj": C(
        "世界首领挑战", "对战", "挑战世界首领并按伤害即时结算奖励。",
        "发送 `世界boss挑战`。", ["打世界boss", "挑战世界首领"],
    ),
    "fight.pokemon_pk_boss_sj_info": C(
        "世界首领信息", "对战", "查看世界首领信息与当前伤害排名。",
        "发送 `世界boss信息`。", ["世界boss信息", "世界首领排行"],
    ),
    "fight.pokemon_pk_boss_sj_paiming": C(
        "世界首领伤害排名", "排行", "查看世界首领伤害排行榜。",
        "发送 `世界boss伤害排名`。", ["世界boss排行榜", "我的世界boss伤害"],
    ),
    "fight.pokemon_pk_dungeon": C(
        "挑战试炼塔", "对战", "挑战精灵试炼塔，逐层提升。",
        "发送 `挑战试炼塔` 或 `挑战精灵塔`。", ["爬试炼塔", "挑战精灵塔"],
    ),
    "fight.pokemon_sd_dungeon": C(
        "扫荡试炼塔", "对战", "扫荡已通关的试炼塔层数。",
        "发送 `扫荡试炼塔`。", ["扫荡精灵塔", "快速扫荡试炼塔"],
    ),
    "fight.pokemon_dungeon_paiming": C(
        "试炼塔排名", "排行", "查看试炼塔通关排名。",
        "发送 `试炼塔排名` 或 `精灵塔排名`。", ["试炼塔排行榜"],
    ),
    "fight.pokemon_pk_pipei": C(
        "匹配对战", "对战", "进入匹配队列，与其他训练家对战并结算段位。",
        "发送 `匹配对战`。", ["匹配对手", "排位对战"],
    ),
    # ---------------------------------------------------------------- 道具
    "prop.pokemon_help_prop": C(
        "道具帮助", "道具", "查看道具商店、携带、使用、交易所等指令。",
        "发送 `道具帮助` 或 `宝可梦道具帮助`。", ["宝可梦道具有哪些用法", "道具怎么用"],
    ),
    "prop.prop_shop_list": C(
        "道具商店", "道具", "查看道具商店在售道具与价格。",
        "发送 `道具商店`。", ["看看道具商店", "商店有什么道具"],
    ),
    "prop.prop_boss_list": C(
        "首领商店", "道具", "查看首领商店可兑换的道具。",
        "发送 `首领商店` 或 `boss商店`。", ["boss商店有什么", "首领商店"],
    ),
    "prop.prop_info": C(
        "道具信息", "道具", "查询一个道具的类型、效果与价格。",
        "发送 `道具信息 道具名`。", ["查询道具效果", "这个道具有什么用"],
    ),
    "prop.buy_random_egg": C(
        "购买随机精灵蛋", "道具", "花费金币购买随机精灵蛋。",
        "发送 `购买随机精灵蛋`。", ["买个随机蛋", "抽精灵蛋"],
    ),
    "prop.prop_send": C(
        "回收道具", "道具", "把道具回收为金币。",
        "发送 `回收道具 道具名 数量`。", ["卖掉道具", "回收道具换钱"],
    ),
    "prop.prop_buy": C(
        "购买道具", "道具", "在道具商店购买道具。",
        "发送 `购买道具 道具名 数量`。", ["买道具", "购买精灵球"],
    ),
    "prop.boss_prop_buy": C(
        "兑换道具", "道具", "用首领币兑换首领商店道具。",
        "发送 `兑换道具 道具名 数量`。", ["兑换boss商店道具"],
    ),
    "prop.prop_xiedai": C(
        "携带道具", "道具", "让宝可梦携带道具（如进化石、Z 纯晶）。",
        "发送 `携带道具 宝可梦名 道具名`。", ["给皮卡丘携带道具"],
    ),
    "prop.prop_xiedai_del": C(
        "取下道具", "道具", "取下宝可梦携带的道具。",
        "发送 `取下道具 宝可梦名`。", ["把皮卡丘的道具取下来"],
    ),
    "prop.prop_use": C(
        "使用道具", "道具", "对宝可梦使用道具（糖果、进化石、王冠等）。",
        "发送 `使用道具 道具名 宝可梦名`。", ["给皮卡丘吃糖果", "使用进化石"],
    ),
    "prop.prop_my_list": C(
        "我的道具", "道具", "查看自己持有的道具与数量。",
        "发送 `我的道具`。", ["看看我的背包", "我有多少道具"],
    ),
    "prop.technical_my_list": C(
        "我的学习机", "道具", "查看自己持有的技能学习机。",
        "发送 `我的学习机` 或 `我的技能机`。", ["我的技能学习机", "查看招式学习机"],
    ),
    "prop.exchange_up_prop": C(
        "交易所上架", "道具", "把道具上架到玩家交易所。",
        "发送 `交易所上架 道具名 数量 单价`。", ["上架道具到交易所", "卖道具给玩家"],
    ),
    "prop.exchange_down_prop": C(
        "交易所下架", "道具", "把交易所中的寄售道具下架。",
        "发送 `交易所下架 道具名`。", ["下架交易所道具"],
    ),
    "prop.show_exchange_list": C(
        "查看交易所", "道具", "查看玩家交易所的在售道具。",
        "发送 `查看交易所`。", ["看看交易所有什么", "玩家交易行"],
    ),
    "prop.exchange_buy_prop": C(
        "交易所购买", "道具", "在玩家交易所购买道具。",
        "发送 `交易所购买 编号`。", ["买交易所的道具"],
    ),
    "prop.show_exchange_list_my": C(
        "我的寄售", "道具", "查看自己在交易所寄售的道具。",
        "发送 `我的寄售`。", ["我上架了什么", "我的交易所订单"],
    ),
    "prop.mew_pm_hongbao": C(
        "pm发红包", "道具", "管理员发放金币红包。",
        "发送 `pm发红包 金额 数量`。", ["发宝可梦红包"], hidden=True,
    ),
    "prop.open_pm_hongbao": C(
        "pm抢红包", "道具", "输入口令抢红包。",
        "发送 `pm抢红包 口令`。", ["抢宝可梦红包"],
    ),
    "prop.add_equip_gacha": C(
        "抽取道具", "道具", "消耗金币抽取随机道具。",
        "发送 `抽取道具`。", ["抽道具", "来一发道具十连"],
    ),
    # ---------------------------------------------------------------- 小游戏
    "pokemon_whois.pokemon_whois": C(
        "我是谁", "小游戏", "根据宝可梦剪影猜名字。",
        "发送 `我是谁`，然后直接发送答案。", ["玩我是谁", "猜宝可梦剪影"],
    ),
    "pokemon_whois.pokemon_whois_tj": C(
        "猜图鉴", "小游戏", "根据图鉴描述猜宝可梦。",
        "发送 `猜图鉴`，然后发送答案。", ["玩猜图鉴", "根据图鉴猜宝可梦"],
    ),
    "pokemon_whois.pokemon_whois_jn": C(
        "猜技能", "小游戏", "根据技能提示猜技能名。",
        "发送 `猜技能`，然后发送答案。", ["玩猜技能", "猜宝可梦技能"],
    ),
    "pokemon_whois.pokemon_shux_this": C(
        "猜属性", "小游戏", "根据克制关系猜属性组合。",
        "发送 `猜属性`，然后发送答案。", ["玩猜属性", "猜宝可梦属性"],
    ),
    "pokemon_whois.pokemon_whois_cc": C(
        "猜精灵", "小游戏", "根据 6 条信息猜宝可梦。",
        "发送 `猜精灵`，然后发送答案。", ["玩猜精灵", "猜宝可梦"],
    ),
    "pokemon_whois.cz_pokemon_whois": C(
        "重置小游戏", "小游戏", "重置当前群的猜宝可梦小游戏状态。",
        "发送 `重置小游戏`。", ["重开小游戏", "重置猜宝可梦"], hidden=True,
    ),
    # ---------------------------------------------------------------- 排行
    "race.start_race_dugou": C(
        "开始赌狗大赛", "排行", "管理员开启一轮赌狗大赛。",
        "发送 `开始赌狗大赛`。", ["开启赌狗大赛"], hidden=True,
    ),
    "race.race_dugou_paiming": C(
        "赌狗大赛排名", "排行", "查看赌狗大赛排名。",
        "发送 `赌狗大赛排名`。", ["赌狗大赛排行榜"],
    ),
    "race.race_dugou_paim": C(
        "查看排名", "排行", "查看赌狗大赛排名或自己的排名。",
        "发送 `查看排名` / `查看我的排名`。", ["查看比赛排名", "查看赌狗大赛榜单"],
    ),
    "race.race_dugou_paim_my": C(
        "查看我的排名", "排行", "查看自己在赌狗大赛中的排名。",
        "发送 `查看我的排名`。", ["我的赌狗排名", "查看我在比赛里的名次"],
    ),
    "race.end_race_dugou": C(
        "赌狗大赛结算", "排行", "管理员结算本轮赌狗大赛。",
        "发送 `赌狗大赛结算`。", ["结算赌狗大赛"], hidden=True,
    ),
    # ---------------------------------------------------------------- 管理
    "map.new_pokemom_show": C(
        "刷新每日大量出现", "管理", "管理员立即刷新每日大量出现宝可梦。",
        "发送 `刷新每日大量出现`。", ["刷新大量出现"], hidden=True,
    ),
    "map.give_prop_pokemon_info": C(
        "发放奖励", "管理", "管理员向指定用户发放道具。",
        "发送 `发放奖励 @用户 道具名 数量`。", ["给玩家发道具"], hidden=True,
    ),
    "map.give_prop_pokemon_info_all": C(
        "全体发放奖励", "管理", "管理员向全体用户发放道具。",
        "发送 `全体发放奖励 道具名 数量`。", ["全服发奖励"], hidden=True,
    ),
    "map.give_pokemon_gm": C(
        "发放精灵", "管理", "管理员向指定用户发放宝可梦。",
        "发送 `发放精灵 @用户 宝可梦名`。", ["给玩家发宝可梦"], hidden=True,
    ),
    "map.update_pokemon_info": C(
        "数据转移", "管理", "管理员把旧账号数据转移到新账号。",
        "发送 `数据转移 旧ID 新ID`。", ["转移宝可梦数据"], hidden=True,
    ),
    "map.get_my_poke_info_sv": C(
        "查看状态", "管理", "管理员查看指定用户或宝可梦的原始状态数据。",
        "发送 `查看状态` 或 `状态查看`。", ["查看玩家数据"], hidden=True,
    ),
    "pokemon_resource.send_download_resource_msg": C(
        "下载全部资源", "资源", "下载全部宝可梦图标与闪光图标素材（约 74MB）。",
        "发送 `pm下载全部资源`。首次游玩可先让插件后台懒下载。", ["下载宝可梦素材"], hidden=True,
    ),
}


def _short(handler: str) -> str:
    parts = handler.split(".")
    return ".".join(parts[-2:])


def _all_handlers() -> Dict[str, List[dict]]:
    grouped: Dict[str, List[dict]] = {}
    for item in list_commands():
        grouped.setdefault(item["handler"], []).append(item)
    return grouped


def _trigger_text(items: List[dict]) -> str:
    parts = []
    for item in items:
        kw = item["keyword"]
        kind = item["type"]
        if kind == "fullmatch":
            parts.append(f"`{kw}`")
        elif kind == "command":
            parts.append(f"`{kw} ...`")
        elif kind == "prefix":
            parts.append(f"`{kw}...`")
        else:
            parts.append(f"`{kw}`")
    return " / ".join(dict.fromkeys(parts))


def _fallback(handler: str, items: List[dict]) -> CatalogEntry:
    first = items[0]
    func = first["keyword"]
    kind = first["type"]
    if kind == "fullmatch":
        brief = f"发送 `{func}` 使用该功能。"
        detail = brief
    else:
        brief = f"发送 `{func}` 加参数使用该功能。"
        detail = f"发送 `{func} 参数`。"
    return CatalogEntry(
        func=func,
        category="基础",
        brief=brief,
        detail=detail,
        intents=[f"宝可梦{func}怎么用", f"帮我使用{func}"],
        hidden=first["pm"] < 6,
    )


def build_entries() -> List[Dict[str, Any]]:
    """返回按分类排序的目录项（含精确触发方式）。"""

    grouped = _all_handlers()
    entries: List[Dict[str, Any]] = []
    for handler, items in grouped.items():
        short = _short(handler)
        entry = CATALOG.get(short) or _fallback(short, items)
        pm = min(item["pm"] for item in items)
        permission = "所有人" if pm >= 6 else ("超级管理员" if pm <= 1 else "群主/管理员")
        trigger_method = _trigger_text(items)
        trigger_condition = "发送对应指令"
        if entry.category in {"管理", "资源"}:
            trigger_condition = f"{permission}可触发"
        entries.append(
            {
                "id": short,
                "handler": handler,
                "func": entry.func,
                "category": entry.category,
                "brief_des": entry.brief,
                "detail_des": entry.detail,
                "trigger_method": trigger_method,
                "trigger_condition": trigger_condition,
                "permission": permission,
                "pmn_hidden": entry.hidden or pm < 6,
                "llm_intents": entry.intents,
                "keywords": list(dict.fromkeys(item["keyword"] for item in items)),
                "types": list(dict.fromkeys(item["type"] for item in items)),
                "triggers": [
                    {"type": item["type"], "value": item["keyword"]}
                    for item in items
                ],
                "interactive": any(item.get("interactive") for item in items),
            }
        )
    order = {name: index for index, name in enumerate(CATEGORY_ORDER)}
    entries.sort(key=lambda e: (order.get(e["category"], 99), e["func"]))
    return entries


def category_index(entries: Optional[List[Dict[str, Any]]] = None) -> Dict[str, List[Dict[str, Any]]]:
    result: Dict[str, List[Dict[str, Any]]] = {}
    for entry in entries or build_entries():
        result.setdefault(entry["category"], []).append(entry)
    return result


def search_entries(query: str, entries: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    query = (query or "").strip().lower()
    if not query:
        return list(entries or build_entries())
    result = []
    for entry in entries or build_entries():
        haystack = " ".join(
            [
                str(entry.get("func", "")),
                str(entry.get("brief_des", "")),
                " ".join(entry.get("keywords", [])),
                " ".join(entry.get("llm_intents", [])),
            ]
        ).lower()
        if query in haystack:
            result.append(entry)
    return result


__all__ = [
    "CATALOG",
    "CATEGORY_ORDER",
    "CatalogEntry",
    "build_entries",
    "category_index",
    "search_entries",
]

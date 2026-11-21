# LLM 工具与 MoEllmChats 接入

七七分支只有一条模型接入路径：

1. `nonebot-plugin-moellmchats` 的强类型 `ToolSpec`；
2. QWeb 宿主 `/qweb/chat` 中用户选择的 New API 模型，由主控把工具桥接给模型。

插件不保存模型/密钥/供应商配置，不提供直连 Agent，也没有 `/api/ai/chat`。
所有工具调用都经过 `nonebot_plugin_pokemon.llm.tools.execute_tool`，因此身份、
数据口径与图表逻辑一致。

## 工具清单

| 工具 | effect | 主要参数 | 返回 |
| --- | --- | --- | --- |
| `pokemon_help_search` | read_only | `query` | 功能目录命中项 |
| `pokemon_player_profile` | read_only | – | 档案、金币、声望、队伍 |
| `pokemon_owned_list` | read_only | `page` | 宝可梦列表 |
| `pokemon_dex_lookup` | read_only | `name` | 图鉴/种族值/进化/技能 |
| `pokemon_move_lookup` | read_only | `name` | 技能信息 |
| `pokemon_item_lookup` | read_only | `name` | 道具信息 |
| `pokemon_type_chart` | read_only | `attack_type`, `defender_types` | 倍率 |
| `pokemon_team_analysis` | read_only | – | 弱点、抗性、建议 |
| `pokemon_global_overview` | read_only | – | 全服统计 |
| `pokemon_leaderboard` | read_only | `kind` | 排行榜 |
| `pokemon_chart` | read_only | `kind` | PNG data URL |
| `pokemon_player_report` | read_only | – | 报告 + 多张图 |
| `pokemon_command` | mutating | `command` | 指令执行结果 |

### 图表类型

- `team_radar`：队伍平均能力雷达图；
- `team_levels`：队伍等级柱状图；
- `team_types`：队伍属性分布饼图；
- `popular_species`：全服热门宝可梦横向柱状图；
- `level_distribution`：全服等级分布折线图。

图表使用 matplotlib（可选依赖 `charts`）。未安装时工具返回文本提示，不影响游戏。

### 数据分析口径

- 队伍分析基于游戏内的种族值、个体值、努力值、性格与技能，不引入外部对战数据；
- 弱点/抗性按 `SHUXING_LIST` 的属性倍率逐成员相乘，统计被克制成员数与最高倍率；
- 全服统计只做聚合（玩家数、记录数、平均等级、热门持有），不返回其他玩家明细；
- 排行榜只返回 UID/昵称/金币/层数等公开字段。

## MoEllmChats 注册

未安装时 `llm/integration.py` 直接返回 `False`，不会让插件加载失败。注册发生在
NoneBot 启动钩子中，因此 `刷新工具` 能捕获到新 generation。

```text
设置工具调用 开
刷新工具
查看LLM状态
```

变更型 `pokemon_command` 使用 `ToolEffect.MUTATING`：

1. 第一次调用只生成一次性确认码；
2. 用户在同一会话发送 `确认执行 <确认码>` 才真正执行；
3. 确认码绑定用户、Bot、会话、generation。

### 菜单与 ToolSpec 的分工

- `PluginMetadata.extra["menu_data"]` / PicMenu 内存目录：告诉模型“用户想做什么”；
- `ToolSpec`：告诉模型“允许用哪些参数调用哪个 handler”；
- 兼容 Matcher 路线仍可用：模型可生成 `野外探索` 等命令，由统一 Matcher 执行。

## 身份与权限

工具上下文的身份只来自可信入口：

- 聊天侧：事件发送者 `sender.role`（`SUPERUSERS` 仅在聊天侧生效）；
- QWeb：宿主 `account.qq` + `account.role`；
- 普通 dict / 对象上下文中的 `is_admin`、`platform` 会被忽略；管理员从 `role`
  重新推导；没有 `user_id` 的玩家类工具直接返回“未识别当前用户身份”。

`pokemon_command` 会把 `user_id` / `role` 传给 `game.runner.run_command`，网页
平台不再用 `SUPERUSERS` 兜底，因此网页用户即使 QQ 在 `SUPERUSERS` 中，也必须由
宿主角色授予管理权限。

## 自定义工具

推荐把新工具加到 `llm/tools.py` 的 `TOOLS` 列表：

```python
ToolDef(
    "pokemon_my_tool",
    "工具说明，告诉模型何时调用。",
    {
        "type": "object",
        "properties": {"arg": {"type": "string"}},
        "required": ["arg"],
        "additionalProperties": False,
    },
    my_handler,  # async def my_handler(*, arg, _ctx: ToolContextData) -> ToolOutcome
    effect="read_only",
)
```

注册、菜单与 QWeb 工具桥会自动读取 `TOOLS`，不需要改第二处。

## 权限

- 工具执行端再次检查用户身份，不只依赖 Schema 隐藏；
- 管理指令（`pm=0/1`）对普通用户返回“需要管理员权限”；
- 网页管理员只由宿主 `account.role` 判定，不读取 `X-QWeb-Is-Admin`，也不使用
  NoneBot `SUPERUSERS` 为网页提权；
- `pokemon_command` 不会绕过游戏内的每日次数、黑名单、队伍状态等业务检查。
# 宝可梦 · NoneBot2 分支

> 本仓库 `qiqi` 分支是 [LoCCai/Pokemon](https://github.com/LoCCai/Pokemon) 的
> **NoneBot2 / QWeb 集成线路**。上游通用分支保持原样；本分支把游戏核心适配到
> NoneBot2，并只通过 MoEllmChats 与宿主 QWeb 认证提供 AI/网页能力。

<p align="center">
  <b>养成 · 探索 · 对战 · 道具 · 小游戏 · QWeb</b><br>
  OneBot v11 / OneBot v12 / QQ 官方机器人
</p>

## 能力

| 能力 | 状态 | 说明 |
| --- | --- | --- |
| 游戏核心 | ✅ 全量移植 | 约 100 个逻辑指令、140+ 触发词；地图、战斗、道具、孵蛋、试炼塔、匹配对战、小游戏 |
| OneBot v11 | ✅ | 文本 / 图片 base64 / @；按钮降级为文本选项 |
| OneBot v12 | ✅ | 文本 / 图片上传 `upload_file` / mention；按钮降级 |
| QQ 官方机器人 | ✅ | 群聊 / C2C / 频道；图片走 `file_image` 自动上传；按钮降级 |
| PicMenu Next | ✅ | `PluginMetadata.extra.menu_data` + 严格 Schema 外部菜单 |
| MoEllmChats | ✅ 可选 | 13 个强类型 `ToolSpec`；菜单意图发现；变更工具二阶段确认 |
| QWeb 网页 | ✅ 宿主认证 | `/qweb/pokemon`、`/qweb/admin/pokemon`；身份/管理员/CSRF 全部交给 `src.qi_web.dependencies` |
| AI 工具 | ✅ 可选 | 只通过 MoEllmChats 暴露 13 个工具；模型由宿主 `/qweb/chat` 中用户选择的 New API 模型决定 |
| 图表 / 分析 | ✅ | 队伍雷达、等级/属性图、全服热门与等级分布、队伍弱点分析 |
| 素材 | ✅ 懒下载 + 占位 | 缺失图标先用占位图，后台补下载；支持全量下载 |

## 安装

### 1. 安装插件

```bash
# 在 NoneBot2 项目根目录
nb plugin install nonebot-plugin-pokemon
# 或开发模式：把仓库放入插件目录，或 pip install -e .
```

### 2. 配置适配器

`pyproject.toml` 示例（按需保留）：

```toml
[tool.nonebot]
adapters = [
  { name = "OneBot V11", module_name = "nonebot.adapters.onebot.v11" },
  { name = "OneBot V12", module_name = "nonebot.adapters.onebot.v12" },
  { name = "QQ", module_name = "nonebot.adapters.qq" },
]
plugins = ["nonebot_plugin_pokemon"]
driver = "~fastapi"
```

`.env` 至少需要：

```dotenv
DRIVER=~fastapi
COMMAND_START=["/"]
SUPERUSERS=["你的QQ号"]
```

QQ 官方机器人还需配置 `QQ_BOTS` / `QQ_IS_SANDBOX` 等官方适配器参数。

### 3. 可选依赖

```bash
pip install "nonebot-plugin-pokemon[onebot11]"   # OneBot v11
pip install "nonebot-plugin-pokemon[onebot12]"   # OneBot v12
pip install "nonebot-plugin-pokemon[qq]"         # QQ 官方机器人
pip install "nonebot-plugin-pokemon[charts]"     # 图表（matplotlib）
pip install "nonebot-plugin-pokemon[web]"        # 网页（fastapi/uvicorn，通常已随 NoneBot2 安装）
```

PicMenu Next 与 MoEllmChats 保持独立安装，未安装时插件仍可正常运行。

## 配置

所有配置都有默认值；字段前缀 `POKEMON_`，写在 `.env` 中。

| 配置 | 默认值 | 说明 |
| --- | --- | --- |
| `POKEMON_ENABLED` | `true` | 总开关 |
| `POKEMON_COMMAND_PREFIXES` | `[]` | 额外命令前缀（NoneBot `COMMAND_START` 已自动处理） |
| `POKEMON_DATA_DIR` | 空 | 数据目录；空则用 localstore / `data/pokemon` |
| `POKEMON_RESOURCE_BASE_URL` | `https://silverwing.elysia.beauty/Pokemon` | 图标素材镜像 |
| `POKEMON_RESOURCE_AUTO_DOWNLOAD` | `true` | 缺图时后台懒下载 |
| `POKEMON_RESOURCE_DOWNLOAD_CONCURRENCY` | `8` | 素材下载并发 |
| `POKEMON_WEB_ENABLED` | `false` | 挂载 QWeb 路由；必须同时能导入宿主认证依赖 |
| `POKEMON_QWEB_ENABLED` | `true` | 是否暴露 QWeb 工具/页面入口（仍受上一项与宿主认证约束） |
| `POKEMON_QWEB_PATH` | `/qweb/pokemon` | QWeb 玩家入口 |
| `POKEMON_QWEB_ADMIN_PATH` | `/qweb/admin/pokemon` | QWeb 管理入口 |
| `POKEMON_INTERACTION_TIMEOUT` | `60` | 战斗/小游戏等待回复秒数 |

> 安全提示：插件不再接受 `X-QWeb-User-Id` / `X-QWeb-Is-Admin` / `X-QWeb-Secret`
> 之类的客户端身份头，也没有游客回退。网页默认关闭；开启时必须由宿主
> `src.qi_web.dependencies` 提供 `require_membership`、`admin_account`、
> `csrf_protected`。离线测试可显式注入依赖。

## 使用

首次游玩：

```text
领取初始精灵 小火龙
更新队伍 小火龙
野外探索
精灵状态 小火龙
```

主帮助：

```text
宝可梦帮助
道具帮助
战斗帮助
小游戏帮助
```

网页：

- QWeb 玩家入口：`http://<host>:<port>/qweb/pokemon`
- QWeb 管理入口：`http://<host>:<port>/qweb/admin/pokemon`

网页包含：训练家面板、功能目录、指令控制台（支持连续交互）、图鉴与数据分析。
页面不再生成/保存本地用户 ID，也不再内置直连模型 AI；写请求会先从宿主同源接口
`/qweb/api/v1/auth/session` 读取 `csrf_token`，再携带 `X-CSRF-Token` 请求头。

## PicMenu Next 适配

插件在 `PluginMetadata.extra["menu_data"]` 中提供 100 条功能目录，每条包含：

- `func` / `brief_des` / `detail_des`
- `trigger_method` / `trigger_condition` / `pmn_triggers`
- `pmn_hidden`（管理/隐藏功能）
- `llm_intents`（AI 意图别名）

同时启动时会把严格 Schema 的外部菜单写到 PicMenu 扫描目录：

```text
<PicMenu 配置的 external_infos 目录>/nonebot_plugin_pokemon.json
```

PicMenu Next 在 Windows 上默认拒绝使用系统级 localstore 路径，建议在 `.env` 加：

```dotenv
LOCALSTORE_USE_CWD=True
```

否则 PicMenu 自身不会加载，插件会退回 `data/picmenu_next/external_infos`。

因此发送 `帮助` 即可在 PicMenu Next 的 QIQI 主题菜单中看到「宝可梦」及其分类功能；
无需修改 PicMenu 配置。未安装 PicMenu Next 时该文件仅作为静态目录保留。

## MoEllmChats 适配

插件不硬依赖 MoEllmChats。安装后启动时自动注册 13 个 `ToolSpec`：

| 工具 | 类型 | 用途 |
| --- | --- | --- |
| `pokemon_help_search` | 只读 | 搜索功能/指令目录 |
| `pokemon_player_profile` | 只读 | 训练家档案、金币、声望、地点、队伍 |
| `pokemon_owned_list` | 只读 | 分页查询拥有的宝可梦 |
| `pokemon_dex_lookup` | 只读 | 图鉴、种族值、进化链、可学技能 |
| `pokemon_move_lookup` | 只读 | 技能信息 |
| `pokemon_item_lookup` | 只读 | 道具信息 |
| `pokemon_type_chart` | 只读 | 属性克制倍率 |
| `pokemon_team_analysis` | 只读 | 队伍弱点/抗性/补强建议 |
| `pokemon_global_overview` | 只读 | 全服统计与热门宝可梦 |
| `pokemon_leaderboard` | 只读 | 金币/图鉴/试炼塔排行 |
| `pokemon_chart` | 只读 | 生成图表并返回图片 |
| `pokemon_player_report` | 只读 | 综合报告（档案 + 分析 + 图表） |
| `pokemon_command` | 变更 | 以当前用户执行一条游戏指令（二阶段确认） |

启用步骤：

1. 安装并配置 `nonebot-plugin-moellmchats`；
2. 发送 `设置工具调用 开`；
3. 发送 `刷新工具`，确认 generation 包含上述工具；
4. 普通用户即可说「帮我看看队伍怕什么属性并画图」，模型会调用工具。

菜单发现与工具调用是两条互补路径：

- 菜单负责“用户想做什么”，让模型知道有哪些游戏功能；
- `ToolSpec` 负责“允许模型用哪些参数调用哪个 handler”。

`pokemon_command` 是变更型工具，首次调用只产生确认码，用户需在同一会话发送
`确认执行 <确认码>`。连续交互的战斗/小游戏不建议由单次工具调用完成，网页或聊天中继续。

## QWeb 接入约定

真实宿主是 `src.qi_web.dependencies`，它必须提供 FastAPI 依赖：

| 依赖 | 作用 |
| --- | --- |
| `require_membership` | 校验登录成员，返回 `account` |
| `admin_account` | 校验管理员，返回 `account` |
| `csrf_protected` | 校验 `X-CSRF-Token` |

插件只读取 `account.qq` 与 `account.role`，不读取请求头、查询参数、Cookie 或请求体
中的身份/群/管理员声明。前端与宿主一样在请求头携带 `X-CSRF-Token`。

插件侧：

- `/qweb/pokemon/api/*`：玩家 API，依赖 `require_membership`；
- `/qweb/admin/pokemon/*`：管理入口，整个前缀都依赖 `admin_account`；
- 所有写请求额外依赖 `csrf_protected`；
- 两种入口共用同一套会话、数据与工具；
- 无宿主依赖时不挂载网页；直接访问默认路由返回 503，不会以游客身份放行；
- 也可以由宿主调用 `nonebot_plugin_pokemon.web.qweb.mount(app, prefix)`，
  但同样必须提供真实认证依赖。

管理 API：

| 路径 | 说明 |
| --- | --- |
| `GET /api/admin/state` | 数据目录、图标数、菜单数、工具注册、调度任务、玩家数 |
| `POST /api/admin/resource/download` | 后台全量下载图标 |
| `POST /api/admin/reload` | 重写外部菜单并重试工具注册 |

更多示例见 [docs/qweb-integration.md](docs/qweb-integration.md)。

## QWeb AI 工具接线

七七分支移除插件自己的模型/密钥/供应商配置、直连 Agent 与 `/api/ai/chat` 路由。
AI 只复用：

1. MoEllmChats 中的 13 个强类型 `ToolSpec`；
2. 宿主 `/qweb/chat` 中用户已选择的 New API 模型。

宿主侧的 QWeb AI 工具接线由主控负责，插件不读取 `providers.toml` /
`model_config.json`，也不发起任何模型 HTTP 请求。`nonebot_plugin_pokemon.qiqi_chat`
只提供宿主可调用的工具桥，身份参数必须来自宿主 `account.qq` / `account.role`。

## 素材

图标共约 1100 张、74MB，未随仓库分发。首次打开缺失图标时：

1. 立即用占位图渲染，指令不失败；
2. 后台按需下载该图标，下次显示真实素材；
3. 管理员可发送 `pm下载全部资源` 或在 QWeb 管理页触发全量下载。

镜像可用 `POKEMON_RESOURCE_BASE_URL` 覆盖。下载失败只影响图片，不影响数值与存档。

## 架构

```text
nonebot_plugin_pokemon/
├── __init__.py              # 入口：元数据、Matcher、启动钩子
├── config.py / paths.py     # 配置与数据目录
├── compat/                  # gsuid_core 兼容层（SV/Event/Bot/图片/调度/日志）
├── platform/                # 协议归一化、发送、交互路由
│   ├── ingress.py           # OneBot v11/v12/QQ -> compat.Event
│   ├── sender.py            # 统一消息 -> 各协议消息
│   ├── interaction.py       # 战斗/小游戏等待队列
│   └── transport.py         # 适配器发送 / 网页捕获
├── matchers/dispatcher.py   # 唯一分发 Matcher（priority=1, block=True）
├── Pokemon/                 # 上游游戏核心（仅改导入与素材兜底）
├── game/                    # 只读数据、分析、图表、指令执行器
├── menu/                    # 指令目录 -> PicMenu / LLM / 网页
├── identity.py              # 可信身份/角色归一化
├── llm/                     # 13 个 ToolSpec 接入（无直连模型 Agent）
├── web/                     # FastAPI 路由、会话、宿主认证适配、静态页
└── resources/               # 素材下载器
```

移植策略：保留上游游戏逻辑，只替换 `gsuid_core` 导入为 `compat` 层；用统一
Matcher 按 `(priority, 触发类型, 命令长度)` 分发，最大程度保持原行为。

## 测试

```bash
pip install pytest pytest-asyncio jsonschema
python -m pytest -q
```

当前包含 100+ 个离线测试：匹配语义、权限、OneBot/QQ 事件归一化、插件加载、菜单覆盖、
PicMenu Schema、QWeb 宿主授权/缺凭证拒绝、连续交互会话、13 项 LLM 工具、图表生成、
素材索引解析。测试不访问真实宿主、在线服务或模型 API。

## 与上游同步

```bash
# 通用分支 nonebot2 保持原样；只在 qiqi 上合入上游改动
git fetch origin nonebot2
git switch qiqi
git merge origin/nonebot2
```

冲突通常集中在 `pokemon_duel/*.py` 的导入行；保持 `nonebot_plugin_pokemon.compat.*`
导入即可。新增素材/数据文件会自动进入包。

## 已知限制

- QQ 官方机器人无法主动向任意群推送（平台限制），`大量出现信息推送` 仅对已注册的
  OneBot v11/v12 Bot 生效；
- OneBot v11 无原生按钮，按钮会降级为文本选项；QQ 官方暂未构造键盘；
- 网页战斗/小游戏依赖长连接式会话，页面刷新会丢失当前连续交互；
- 插件不再提供独立网页/游客模式；脱离宿主时网页默认关闭，直接访问返回 503；
- 后台懒下载受镜像速度影响，首次查看部分宝可梦可能显示占位图；
- MoEllmChats 的文件/生成工具隔离能力在 Windows 上受限，与本插件无关；
- 聊天管理指令沿用上游 `pm` 规则：`pm=0` 仅超级管理员，`pm=1` 超级管理员，
  `pm=2/3` 群主/管理员；网页管理员只由宿主 `account.role` 决定，`SUPERUSERS`
  不参与网页提权。

## 许可

GPL-3.0-or-later。游戏核心与素材来自上游 Pokemon 项目，版权归原作者所有。
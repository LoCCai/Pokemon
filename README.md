# 宝可梦 · NoneBot2 分支

> 本仓库分支 `nonebot2` 是 [LoCCai/Pokemon](https://github.com/LoCCai/Pokemon) 的
> **NoneBot2 移植线路**。上游 `main` 继续服务 gsuid_core；本分支把同一套游戏核心
> 适配到 NoneBot2 的统一事件模型，并补齐菜单、LLM 工具与 QWeb 网页游玩基底。

<p align="center">
  <b>养成 · 探索 · 对战 · 道具 · 小游戏 · 网页 · AI</b><br>
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
| QWeb 网页 | ✅ 基底 | `/qweb/pokemon`、`/qweb/admin/pokemon`、独立 `/pokemon` |
| 网页 AI | ✅ | OpenAI 兼容 Function Calling，复用同一套游戏工具；可复用 MoEllmChats 模型配置 |
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
| `POKEMON_WEB_ENABLED` | `true` | 挂载网页路由 |
| `POKEMON_WEB_PATH` | `/pokemon` | 独立网页入口 |
| `POKEMON_QWEB_PATH` | `/qweb/pokemon` | QWeb 玩家入口 |
| `POKEMON_QWEB_ADMIN_PATH` | `/qweb/admin/pokemon` | QWeb 管理入口 |
| `POKEMON_QWEB_USER_HEADER` | `X-QWeb-User-Id` | 宿主注入的用户身份头 |
| `POKEMON_QWEB_NAME_HEADER` | `X-QWeb-User-Name` | 宿主注入的昵称头 |
| `POKEMON_QWEB_ADMIN_HEADER` | `X-QWeb-Is-Admin` | 宿主注入的管理员标记 |
| `POKEMON_QWEB_SECRET` | 空 | 可选共享密钥；设置后 QWeb 路由要求 `X-QWeb-Secret` |
| `POKEMON_WEB_ALLOW_GUEST` | `true` | 无身份头时允许游客 |
| `POKEMON_LLM_ENABLED` | `true` | 网页 AI 开关 |
| `POKEMON_LLM_PROVIDER` | `auto` | `auto` / `openai` / `moellmchats` / `off` |
| `POKEMON_LLM_BASE_URL` | 空 | OpenAI 兼容 Base URL（含 `/v1`） |
| `POKEMON_LLM_API_KEY` | 空 | API Key |
| `POKEMON_LLM_MODEL` | `gpt-4o-mini` | 模型名 |
| `POKEMON_LLM_TEMPERATURE` | `0.4` | 采样温度 |
| `POKEMON_LLM_MAX_STEPS` | `6` | 工具循环上限 |
| `POKEMON_INTERACTION_TIMEOUT` | `60` | 战斗/小游戏等待回复秒数 |

> 安全提示：`POKEMON_QWEB_SECRET` 只适合反向代理注入；不要把它写进前端代码。
> 独立 `/pokemon` 默认无登录，公网部署请自行加认证或关闭 `POKEMON_WEB_ENABLED`。

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

- 独立入口：`http://<host>:<port>/pokemon`
- QWeb 玩家入口：`http://<host>:<port>/qweb/pokemon`
- QWeb 管理入口：`http://<host>:<port>/qweb/admin/pokemon`

网页包含：训练家面板、功能目录、指令控制台（支持连续交互）、图鉴、数据分析与 AI 助手。

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

QWeb 宿主（参考 `meme_manager` 的 `qiqi` 分支）通常在反向代理或宿主中间件中完成登录、
管理员校验与审计，再把身份注入给插件：

```http
X-QWeb-User-Id: 123456
X-QWeb-User-Name: 小智
X-QWeb-Is-Admin: 1
X-QWeb-Secret: <可选共享密钥>
```

插件侧：

- `/qweb/pokemon/api/*`：玩家 API；
- `/qweb/admin/pokemon/api/*`：管理 API（需要 `X-QWeb-Is-Admin`）；
- 两种入口共用同一套会话、数据与工具；
- `POKEMON_QWEB_SECRET` 非空时校验 `X-QWeb-Secret`；
- 也可以由宿主直接 `app.include_router(router, prefix="/your/path")`，
  或调用 `nonebot_plugin_pokemon.web.qweb.mount(app, prefix)`。

管理 API：

| 路径 | 说明 |
| --- | --- |
| `GET /api/admin/state` | 数据目录、图标数、菜单数、工具注册、调度任务、玩家数 |
| `POST /api/admin/resource/download` | 后台全量下载图标 |
| `POST /api/admin/reload` | 重写外部菜单并重试工具注册 |

更多示例见 [docs/qweb-integration.md](docs/qweb-integration.md)。

## 网页 AI

网页 AI 使用 OpenAI 兼容的 Function Calling，和 MoEllmChats 共用
`nonebot_plugin_pokemon.llm.tools` 中的工具定义与执行器。

配置优先级：

1. `POKEMON_LLM_BASE_URL` / `POKEMON_LLM_API_KEY` / `POKEMON_LLM_MODEL`；
2. `POKEMON_LLM_PROVIDER=moellmchats`（或 `auto` 且自身未配置）时，读取
   MoEllmChats 的 `providers.toml` 与 `model_config.json`；
3. `OPENAI_BASE_URL` / `OPENAI_API_KEY` / `OPENAI_MODEL` 环境变量。

未配置模型时网页仍可正常游玩，AI 面板会提示配置方法。

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
├── llm/                     # ToolSpec 接入 + 网页 Agent
├── web/                     # FastAPI 路由、会话、QWeb 适配、静态页
└── resources/               # 素材下载器
```

移植策略：保留上游游戏逻辑，只替换 `gsuid_core` 导入为 `compat` 层；用统一
Matcher 按 `(priority, 触发类型, 命令长度)` 分发，最大程度保持原行为。

## 测试

```bash
pip install pytest pytest-asyncio jsonschema
python -m pytest -q
```

当前包含 82 个测试：匹配语义、权限、OneBot/QQ 事件归一化、插件加载、菜单覆盖、
PicMenu Schema、网页 API、连续交互会话、LLM 工具与 Agent 工具循环、图表生成、素材索引解析。

## 与上游同步

```bash
git fetch upstream
git switch nonebot2
git merge upstream/main
```

冲突通常集中在 `pokemon_duel/*.py` 的导入行；保持 `nonebot_plugin_pokemon.compat.*`
导入即可。新增素材/数据文件会自动进入包。

## 已知限制

- QQ 官方机器人无法主动向任意群推送（平台限制），`大量出现信息推送` 仅对已注册的
  OneBot v11/v12 Bot 生效；
- OneBot v11 无原生按钮，按钮会降级为文本选项；QQ 官方暂未构造键盘；
- 网页战斗/小游戏依赖长连接式会话，页面刷新会丢失当前连续交互；
- 后台懒下载受镜像速度影响，首次查看部分宝可梦可能显示占位图；
- MoEllmChats 的文件/生成工具隔离能力在 Windows 上受限，与本插件无关；
- 管理指令沿用上游 `pm` 规则：`pm=0` 仅超级管理员，`pm=1` 超级管理员，
  `pm=2/3` 群主/管理员。

## 许可

GPL-3.0-or-later。游戏核心与素材来自上游 Pokemon 项目，版权归原作者所有。
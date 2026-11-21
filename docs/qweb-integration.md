# QWeb 网页接入（qiqi 分支）

本插件把网页当成“第四种协议”：它和 OneBot v11 / v12 / QQ 官方机器人共享同一套
游戏指令、权限与数据，只是把出站消息收集到 `WebTransport` 而不是发到聊天平台。

本分支不提供独立网页服务，也不接受客户端声明的身份。网页认证完全交给真实宿主
`src.qi_web.dependencies`。

## 宿主必须提供的依赖

```python
# src.qi_web/dependencies.py（宿主侧，示意）
from fastapi import Depends, Header, HTTPException, Request


async def require_membership(request: Request):
    account = await load_logged_in_account(request)
    if account is None:
        raise HTTPException(401, "未登录")
    return account


async def admin_account(account=Depends(require_membership)):
    if account.role not in {"admin", "owner"}:
        raise HTTPException(403, "需要管理员")
    return account


async def csrf_protected(x_csrf_token: str = Header(..., alias="X-CSRF-Token")):
    if not verify_csrf(x_csrf_token):
        raise HTTPException(403, "CSRF 校验失败")
```

插件只依赖这三个名字，并只从 `account` 读取：

- `account.qq` → 游戏用户 ID；
- `account.role` → 管理员角色；
- `account.nickname` / `username` / `name`（可选）→ 展示名，缺省回退到 QQ。

不读取 `account.user_id`、`account.is_admin`、请求头、查询参数、Cookie 或请求体
中的身份/群/权限声明。

## 路由

默认挂载两个前缀（只在 `POKEMON_WEB_ENABLED=true` 且成功导入宿主依赖时）：

| 前缀 | 用途 | FastAPI 依赖 |
| --- | --- | --- |
| `/qweb/pokemon` | QWeb 玩家入口 | `require_membership` |
| `/qweb/admin/pokemon` | QWeb 管理入口（整个前缀） | `admin_account` |

所有 `POST`/写操作额外依赖 `csrf_protected`。健康检查 `GET /api/health` 不需要
身份，便于宿主探活。

同一套 API：

```text
GET  /api/health
GET  /api/bootstrap
GET  /api/menu?q=
GET  /api/session?operation=...&offset=...
GET  /api/player
GET  /api/pokedex?name=皮卡丘
GET  /api/charts/{kind}
GET  /api/leaderboard/{score|pokedex|dungeon}
POST /api/command         {"text": "野外探索"}
POST /api/cancel
GET  /api/admin/state
POST /api/admin/resource/download
POST /api/admin/reload
```

`kind` 支持：`team_radar`、`team_levels`、`team_types`、`popular_species`、
`level_distribution`。

插件不再提供 `/api/ai/chat`，也不读取任何模型配置；QWeb AI 由主控接线，模型使用
`/qweb/chat` 中用户选择的 New API 模型。

## 前端

`web/static/index.html` 不再生成或保存 `uid`，也不再发送
`X-Pokemon-User` / `X-QWeb-Is-Admin`。它和宿主页面一样，对非 GET 请求先从宿主
同源接口读取会话 CSRF token：

```http
GET /qweb/api/v1/auth/session
```

响应中的 `csrf_token` 会放进写请求（`POST` 等）的请求头：

```http
X-CSRF-Token: <宿主下发的 token>
```

如果宿主使用其他会话/CSRF 接口，请在本分支调整 `index.html` 顶部的
`csrfToken()`，但不要回退到客户端声明 QQ/管理员。

## 挂载示例

方式一：交给插件启动钩子自动挂载（需 `POKEMON_WEB_ENABLED=true` 且宿主依赖可导入）：

```dotenv
POKEMON_WEB_ENABLED=true
POKEMON_QWEB_PATH=/qweb/pokemon
POKEMON_QWEB_ADMIN_PATH=/qweb/admin/pokemon
```

方式二：宿主自己挂载：

```python
from nonebot_plugin_pokemon.web.qweb import mount

mount(app, prefix="/qweb/games/pokemon")
```

`mount()` 会再次导入宿主依赖；找不到时直接抛 `RuntimeError`，不会创建一个没有
认证的空壳路由。

方式三：离线测试显式注入：

```python
from fastapi import FastAPI
from nonebot_plugin_pokemon.web.app import setup_web
from nonebot_plugin_pokemon.web.auth import AuthDependencies

auth = AuthDependencies(
    require_membership=fake_membership,
    admin_account=fake_admin,
    csrf_protected=fake_csrf,
)
app = FastAPI()
setup_web(app, auth=auth, force=True)
```

这仅用于测试。生产环境必须使用真实宿主依赖。

## 身份与权限

- 网页普通用户：`tool context user_id = account.qq`，`group_id=None`；
- 网页管理员：`is_admin = account.role in ADMIN_ROLES`；
- NoneBot `SUPERUSERS` **不参与**网页提权；
- 连续交互（战斗/小游戏）每一轮都使用当前会话保存的角色；角色变更只来自宿主
  下一次校验结果，不能由请求体覆盖；
- 新指令开始时会清理上一轮等待事件与出站消息，避免旧连续交互泄漏到新指令。

## 管理 API

`GET /api/admin/state` 返回：

- 数据目录、图标/闪光图标数量；
- 菜单条目数、工具注册状态与 13 项工具数量；
- 调度任务名；
- 玩家数、宝可梦记录数；
- 活跃网页会话数。

`POST /api/admin/resource/download`：后台全量下载 1100 张图标（约 74MB），
立即返回 `accepted`，完成后写日志。

`POST /api/admin/reload`：重写 PicMenu 外部菜单，并重试 MoEllmChats 工具注册。
适合 QWeb 宿主在热更新后调用。

## 网页会话与连续交互

战斗、小游戏会调用 `receive_resp` 等待下一条消息。网页侧：

1. 第一次 `POST /api/command` 启动指令，返回 `awaiting=true` 和按钮；
2. 后续 `POST /api/command` 直接把输入投递给等待队列；长耗时指令可用
   `GET /api/session?operation=...&offset=...` 轮询新输出；
3. `POST /api/cancel` 取消当前连续交互；
4. 网页打开或刷新时读取 `GET /api/session` 恢复当前回合。主进程重启或引擎超时后，需要重新发起行动。

游戏页通过 `GET /api/game/world` 读取训练家、队伍、地图、背包和开放地点。精灵立绘由
`GET /api/game/sprite/{id}` 提供。选择伙伴、移动、探索、出招等操作发送到
`POST /api/game/action`，请求带宿主 CSRF 以及上个快照的 `operation` 和 `offset`。
收到 409 时重新读取会话。野外遭遇的双方 HP、等级和招式由正在运行的战斗提供。

服务端每个 `qweb:<qq>` 一个会话，串行执行；群 ID 不来自网页请求，网页会话固定
不绑定群。相同 QQ 在不同宿主账号角色下会更新角色，但不会保留旧的管理员状态。

## 未接通项

- 宿主 QWeb AI 工具接线（把 `qiqi_chat` 接到 `/qweb/chat` 的模型工具列表）由主控
  处理，不属于本分支的插件路由；
- 插件不保存/读取 New API 模型选择，插件侧没有模型配置；
- 真实宿主登录、CSRF 生成规则、审计与限流需在宿主侧联调，离线测试只验证
  FastAPI 依赖契约。
# QWeb 网页接入

本插件把网页当成“第四种协议”：它和 OneBot v11 / v12 / QQ 官方机器人共享同一套
游戏指令、权限与数据，只是把出站消息收集到 `WebTransport` 而不是发到聊天平台。

## 路由

默认挂载三个前缀：

| 前缀 | 用途 | 认证 |
| --- | --- | --- |
| `/pokemon` | 独立网页 | 可选（游客模式） |
| `/qweb/pokemon` | QWeb 玩家入口 | 宿主身份头 |
| `/qweb/admin/pokemon` | QWeb 管理入口 | `X-QWeb-Is-Admin` |

同一套 API：

```text
GET  /api/health
GET  /api/bootstrap
GET  /api/menu?q=
POST /api/command         {"text": "野外探索"}
POST /api/cancel
POST /api/ai/chat         {"message": "...", "history": [...]}
GET  /api/player
GET  /api/pokedex?name=皮卡丘
GET  /api/charts/{kind}
GET  /api/leaderboard/{score|pokedex|dungeon}
GET  /api/admin/state
POST /api/admin/resource/download
POST /api/admin/reload
```

`kind` 支持：`team_radar`、`team_levels`、`team_types`、`popular_species`、
`level_distribution`。

## 身份注入

宿主在反向代理或中间件中完成登录/管理员校验后注入：

```http
X-QWeb-User-Id: 123456
X-QWeb-User-Name: %E5%B0%8F%E6%99%BA
X-QWeb-Is-Admin: 1
X-QWeb-Secret: <仅在设置了 POKEMON_QWEB_SECRET 时需要>
```

昵称使用 URL 编码，插件会 `unquote`。没有身份头时：

- `POKEMON_WEB_ALLOW_GUEST=true`（默认）使用 `POKEMON_WEB_DEFAULT_USER`；
- 否则返回 401。

### Nginx 示例

```nginx
location /qweb/pokemon/ {
    # 只允许宿主注入，先清空客户端传入的同名头
    proxy_set_header X-QWeb-User-Id "";
    proxy_set_header X-QWeb-User-Name "";
    proxy_set_header X-QWeb-Is-Admin "";
    proxy_set_header X-QWeb-Secret "";

    # 由 auth_request 或宿主网关注入真实身份
    auth_request /qweb/auth;
    auth_request_set $qweb_uid $upstream_http_x_qweb_user_id;
    proxy_set_header X-QWeb-User-Id $qweb_uid;

    proxy_pass http://127.0.0.1:8080;
}
```

> 关键点：代理必须先清空客户端自带的 `X-QWeb-*`，再写入可信值，否则任何用户都能
> 伪造管理员。

## 宿主直接挂载

如果宿主不想使用默认前缀：

```python
from nonebot_plugin_pokemon.web.qweb import mount

mount(app, prefix="/qweb/games/pokemon")
```

或者自己 `include_router`：

```python
from nonebot_plugin_pokemon.web.app import router
app.include_router(router, prefix="/qweb/games/pokemon")
```

## Feature Catalog

QWeb / MoEllmChats 的意图目录可以读取：

```python
from nonebot_plugin_pokemon.web.qweb import feature_catalog

catalog = feature_catalog()
# {
#   "plugin_id": "nonebot_plugin_pokemon",
#   "name": "宝可梦",
#   "version": "...",
#   "features": [
#     {"id": ..., "name": ..., "summary": ..., "triggers": [...],
#      "llm_intents": [...], "hidden": False, "permission": "所有人", ...}
#   ]
# }
```

功能目录与 `PluginMetadata.extra["menu_data"]`、PicMenu 外部菜单同源，避免三份数据漂移。

## 管理 API

`GET /api/admin/state` 返回：

- 数据目录、图标/闪光图标数量；
- 菜单条目数、工具是否已注册；
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
2. 后续 `POST /api/command` 直接把输入投递给等待队列；
3. `POST /api/cancel` 取消当前连续交互；
4. 页面刷新会丢失等待队列，需要重新发起。

服务端每个 `(user_id, group_id)` 一个会话，串行执行，避免同一玩家并发改存档。

## 后续开发建议

- 把 `web/session.py` 的 `WebTransport` 替换为 WebSocket / SSE 流式输出；
- 在 `web/qweb.py` 中增加宿主的审计、限流、Feature Catalog 版本字段；
- 新增页面直接调用现有 `/api/*`，不要复制游戏逻辑；
- 新游戏功能仍写在 `Pokemon/` 或 `game/`，网页与聊天自动共享。
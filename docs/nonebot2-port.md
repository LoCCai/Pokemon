# NoneBot2 移植说明

## 目标

把 gsuid_core 版 Pokemon 的核心玩法原样搬到 NoneBot2，同时不把上游代码改得无法
同步。策略是“**逻辑保留，边界替换**”：

- 游戏数据、战斗公式、地图、绘图、数据库全部保留；
- 只把 `gsuid_core` 的 SV / Event / Bot / 消息段 / 图片转换 / 调度 / 日志替换为
  `nonebot_plugin_pokemon.compat`；
- 用一个 Matcher 统一分发所有上游触发器，避免把 140 个触发词逐个改写成 NoneBot
  的 `on_command`。

## 调用链

```text
OneBot v11/v12/QQ 事件
  -> platform.ingress.to_event        # 归一化：user_id/group_id/text/at/sender/role
  -> matchers.dispatcher._rule        # 交互等待？游戏触发器？
  -> compat.sv.SV.find                # (priority, 类型, 命令长度) 选唯一命中
  -> compat.Bot + AdapterTransport    # send / send_option / receive_resp
  -> 上游 handler                      # 原封不动的游戏逻辑
  -> platform.sender                  # 文本/图片/按钮 -> 协议消息
```

网页：

```text
POST /api/command
  -> web.session.WebSessionRegistry   # 每会话串行、可连续交互
  -> 同一个 SV.find / handler
  -> WebTransport 收集出站消息
  -> JSON（文本 + 图片 data URL + 按钮 + awaiting）
```

## 匹配语义

兼容层尽量复刻 gsuid_core：

- `on_fullmatch`：忽略首尾空白后完全相等；
- `on_command`：命令词开头，余下为参数；中英文交界可省略空格；
- `on_prefix`：命令词开头且必须有后续内容；
- 排序：`priority` 升序 -> 类型（fullmatch < command < prefix）-> 关键词长度降序；
- 命令前缀：NoneBot `COMMAND_START`（默认 `/`）在入站时去掉；
- `@` 段从正文剥离，`at`/`is_tome` 单独保留给需要 @ 的指令。

## 权限

沿用上游 SV 的 `pm`：

| pm | 含义 | 本分支判定 |
| --- | --- | --- |
| 0 | 主人 | 仅 NoneBot `SUPERUSERS` |
| 1 | 超级用户 | 仅 `SUPERUSERS` |
| 2 | 群主 | 群主 |
| 3 | 群管理员 | 群主/管理员 |
| 6 | 普通用户 | 所有人 |

网页管理员通过 `X-QWeb-Is-Admin` 或 `SUPERUSERS` 获得 pm<=1 能力。

## 交互等待

上游战斗/小游戏依赖 `bot.receive_resp` / `receive_mutiply_resp`。兼容层实现：

- `InteractionBroker` 按 `platform:bot:self:scene` 保存等待队列；
- 分发 Matcher 在规则阶段先查等待队列，命中则把事件投递进去并阻断后续命令；
- `WebSessionRegistry` 为网页会话保留同一个任务，支持多轮输入；
- 超时返回 `None`，与上游行为一致。

## 协议差异

| 能力 | OneBot v11 | OneBot v12 | QQ 官方 |
| --- | --- | --- | --- |
| 文本 | ✅ | ✅ | ✅ |
| 图片 | `base64://` | `upload_file` 后 `file_id` | `file_image` 自动上传 |
| @ | ✅ | `mention` | `mention_user`（群） |
| 按钮 | 降级文本 | 降级文本 | 降级文本 |
| 主动推送 | ✅ | ✅ | ❌（平台限制） |

QQ 官方 C2C 不发送 @；图片统一转 JPEG；发送失败只记录日志，不抛出到游戏逻辑。

## 素材兜底

上游直接 `Image.open(CHAR_ICON_PATH / ...)`，缺图会中断绘图。本分支：

- 所有 `Image.open` 替换为 `compat.media.open_image`；
- 缺失时返回占位图，并把路径排进后台下载队列；
- 下载器按资源镜像目录索引补文件，`.part` 原子替换；
- `convert_img` 同样走兜底，避免“领到宝可梦但发不出图”。

## 与上游同步

上游改动通常落在 `Pokemon/pokemon_duel/*.py`。合并时：

1. 保留新逻辑；
2. 把新增的 `from gsuid_core...` 替换为 `nonebot_plugin_pokemon.compat...`；
3. 若新增 `Image.open`，替换为 `open_image`；
4. 若新增 `SV.on_*` 触发器，菜单目录会自动多一条（fallback），建议在
   `menu/catalog.py` 补一条可读描述与 `llm_intents`；
5. 运行 `pytest -q` 与 `python -m build --wheel`。

## 测试边界

- 单元测试不依赖真实 QQ/OneBot 连接；
- OneBot v11 使用真实适配器事件模型验证归一化；
- v12/QQ 使用 duck-typed 假事件验证字段映射；
- 网页 API 使用 FastAPI TestClient；
- LLM Agent 使用 mock completion 验证工具循环，不访问外网；
- 图表测试验证 PNG 头，不比较像素。

真实协议联调仍需在测试 Bot 上完成：适配器连接、图片上传、按钮降级、群权限、
QQ 官方审核与频控都不包含在离线测试中。
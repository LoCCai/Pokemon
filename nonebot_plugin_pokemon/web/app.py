"""QWeb 网页 API 与静态页面。

安全边界：

* 所有业务路由都依赖宿主 FastAPI 依赖（``require_membership`` /
  ``admin_account`` / ``csrf_protected``）；
* 身份只来自宿主返回的 ``account.qq``，管理员只来自 ``account.role``；
* 请求头、查询参数、Cookie、请求体都不能声明 user/group/admin；
* 没有宿主认证时不挂载网页；显式访问默认路由返回 503，而不是游客身份。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from ..compat.logger import logger
from ..config import plugin_config
from ..game import analytics, charts, repository
from ..game import world as game_world
from ..game.actions import ActionError
from ..game.data import dex_entry, display_name, item_entry, move_entry, resolve_pokemon
from ..llm.tools import TOOLS, ToolContextData
from ..menu import PLUGIN_ID, VERSION, external_menu, help_cards
from ..menu.catalog import build_entries, category_index, search_entries as search_menu
from ..paths import STATIC_DIR, pokemon_data_dir
from .auth import (
    AuthDependencies,
    HOST_MODULE,
    WebAccount,
    admin_account_dependency,
    load_host_auth,
    member_account_dependency,
    unavailable_auth,
)
from .session import registry

_SPRITE_MEDIA = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


class GameActionPayload(BaseModel):
    """Typed action shape. Extra fields are ignored and never trusted."""

    action: str
    value: Any = None
    operation: str = ""
    offset: int = Field(default=0, ge=0)


def _sprite_path(pid: int) -> Optional[str]:
    """Resolve genuine local art by the exact name the core uses; no user path."""

    base = pokemon_data_dir() / "resource" / "icon"
    names = [display_name(pid), str(pid)]
    for name in dict.fromkeys(names):
        for suffix in _SPRITE_MEDIA:
            candidate = base / f"{name}{suffix}"
            try:
                if candidate.is_file() and candidate.stat().st_size > 0:
                    return str(candidate)
            except OSError:
                continue
    return None


def _sprite_response(path: Optional[str], pid: int) -> Response:
    if path:
        media = _SPRITE_MEDIA.get(Path(path).suffix.lower(), "application/octet-stream")
        return FileResponse(
            path,
            media_type=media,
            headers={
                "Cache-Control": "private, max-age=86400",
                "X-Pokemon-Sprite": "local",
                "X-Pokemon-Sprite-Id": str(pid),
                "X-Content-Type-Options": "nosniff",
            },
        )
    try:
        from ..resources.downloader import enqueue_missing

        enqueue_missing(pokemon_data_dir() / "resource" / "icon" / f"{display_name(pid)}.png")
    except Exception:
        pass
    fallback = STATIC_DIR / "pokemon-fallback.png"
    if fallback.is_file():
        return FileResponse(
            fallback,
            media_type="image/png",
            headers={
                "Cache-Control": "private, max-age=20",
                "X-Pokemon-Sprite": "fallback",
                "X-Pokemon-Sprite-Id": str(pid),
                "X-Content-Type-Options": "nosniff",
            },
        )
    # Defensive last resort: a deterministic packaged PNG is still required.
    import base64

    return Response(
        content=base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        ),
        media_type="image/png",
        headers={
            "Cache-Control": "private, max-age=86400",
            "X-Pokemon-Sprite": "fallback",
            "X-Pokemon-Sprite-Id": str(pid),
            "X-Content-Type-Options": "nosniff",
        },
    )


def _asset_response(filename: str, media_type: str) -> FileResponse:
    # Exact filename allow-list only; callers never supply a path.
    file = STATIC_DIR / filename
    if not file.is_file():
        raise HTTPException(status_code=404, detail="静态资源缺失")
    return FileResponse(
        file,
        media_type=media_type,
        headers={"Cache-Control": "private, max-age=300", "X-Content-Type-Options": "nosniff"},
    )


def account_context(account: WebAccount) -> ToolContextData:
    """把宿主账号转换成游戏工具上下文；群/权限不接受客户端输入。"""

    return account.to_context(platform="qweb")


def create_router(auth: AuthDependencies, *, admin_only: bool = False) -> APIRouter:
    """用指定宿主依赖创建路由。测试可注入假的三个依赖。

    ``admin_only=True`` 用于管理前缀：连普通玩家 API 也要求宿主管理员依赖，
    避免成员通过 ``/qweb/admin/pokemon`` 使用非管理路由。
    """

    router = APIRouter()
    require_member = member_account_dependency(auth)
    require_admin = admin_account_dependency(auth)
    base_dependency = require_admin if admin_only else require_member
    csrf = Depends(auth.csrf_protected)

    async def member_context(account: WebAccount = Depends(base_dependency)) -> ToolContextData:
        return account_context(account)

    async def admin_context(account: WebAccount = Depends(require_admin)) -> ToolContextData:
        return account_context(account)

    # ----------------------------------------------------------------- 公共
    @router.get("/api/health")
    async def health() -> Dict[str, Any]:
        return {"ok": True, "plugin": PLUGIN_ID, "version": VERSION}

    # ----------------------------------------------------------------- 玩家
    @router.get("/api/catalog")
    async def catalog(_ctx: ToolContextData = Depends(member_context)) -> Dict[str, Any]:
        return {
            "plugin_id": PLUGIN_ID,
            "name": "宝可梦",
            "version": VERSION,
            "description": "宝可梦养成、探索、对战、道具与小游戏",
            "menu_data": build_entries(),
            "external_menu": external_menu(),
        }

    @router.get("/api/menu")
    async def menu(
        q: str = Query(default=""),
        _ctx: ToolContextData = Depends(member_context),
    ) -> Dict[str, Any]:
        entries = search_menu(q) if q else build_entries()
        return {
            "categories": category_index(entries),
            "cards": help_cards(),
            "total": len(entries),
        }

    @router.get("/api/bootstrap")
    async def bootstrap(ctx: ToolContextData = Depends(member_context)) -> Dict[str, Any]:
        profile = await repository.profile(ctx.user_id)
        return {
            "identity": {
                "user_id": ctx.user_id,
                "user_name": ctx.user_name,
                "is_admin": ctx.is_admin,
                "platform": ctx.platform,
            },
            "profile": profile,
            "menu": help_cards(),
            "tools": {"count": len(TOOLS), "host": HOST_MODULE},
            "version": VERSION,
        }

    @router.get("/api/player")
    async def player(
        ctx: ToolContextData = Depends(member_context),
        uid: str = Query(default=""),
    ) -> Dict[str, Any]:
        target = uid if uid and ctx.is_admin else ctx.user_id
        profile = await repository.profile(target)
        owned = await repository.owned(target, 0)
        return {"profile": profile, "owned": owned}

    @router.get("/api/pokedex")
    async def pokedex(
        _ctx: ToolContextData = Depends(member_context),
        name: str = Query(default=""),
        q: str = Query(default=""),
    ) -> Dict[str, Any]:
        if name:
            data = dex_entry(name)
            if not data:
                raise HTTPException(status_code=404, detail="没有找到该宝可梦")
            return {"entry": data}
        if q:
            lowered = q.casefold()
            from ..game.data import all_pokemon

            items = [
                item
                for item in all_pokemon()
                if lowered in item["name"].casefold() or lowered in str(item["id"])
            ][:50]
            return {"items": items}
        return {"items": []}

    @router.get("/api/move")
    async def move(
        _ctx: ToolContextData = Depends(member_context),
        name: str = Query(...),
    ) -> Dict[str, Any]:
        data = move_entry(name)
        if not data:
            raise HTTPException(status_code=404, detail="没有找到该技能")
        return {"entry": data}

    @router.get("/api/item")
    async def item(
        _ctx: ToolContextData = Depends(member_context),
        name: str = Query(...),
    ) -> Dict[str, Any]:
        data = item_entry(name)
        if not data:
            raise HTTPException(status_code=404, detail="没有找到该道具")
        return {"entry": data}

    @router.get("/api/analytics/overview")
    async def overview(_ctx: ToolContextData = Depends(member_context)) -> Dict[str, Any]:
        return await analytics.global_overview()

    @router.get("/api/leaderboard/{kind}")
    async def leaderboard(
        kind: str,
        _ctx: ToolContextData = Depends(member_context),
    ) -> Dict[str, Any]:
        if kind == "dungeon":
            items = await repository.dungeon_leaderboard()
        elif kind == "pokedex":
            items = await repository.pokedex_leaderboard()
        else:
            items = await repository.score_leaderboard()
        return {"kind": kind, "items": items}

    @router.get("/api/charts/{kind}")
    async def chart(
        kind: str,
        ctx: ToolContextData = Depends(member_context),
        uid: str = Query(default=""),
    ) -> Response:
        target = uid if uid and ctx.is_admin else ctx.user_id
        profile = await repository.profile(target)
        analysis = analytics.team_analysis(profile.get("team", []))
        if kind in {"team_radar", "team_levels", "team_types"}:
            images = charts.team_charts(profile, analysis)
        elif kind in {"popular_species", "level_distribution"}:
            images = charts.global_charts(await analytics.global_overview())
        else:
            raise HTTPException(status_code=404, detail="未知图表")
        data = images.get(kind)
        if not data:
            raise HTTPException(status_code=404, detail="暂无数据")
        return Response(content=data, media_type="image/png", headers={"Cache-Control": "no-store"})

    @router.get("/api/session")
    async def session_status(operation: str = "", offset: int = Query(0, ge=0),
                             ctx: ToolContextData = Depends(member_context)) -> Dict[str, Any]:
        session = registry.get(ctx.user_id, None, ctx.user_name, ctx.is_admin, ctx.role)
        return registry.status(session, operation, offset)

    @router.post("/api/command", dependencies=[csrf])
    async def command(
        ctx: ToolContextData = Depends(member_context),
        payload: Dict[str, Any] = Body(...),
    ) -> Dict[str, Any]:
        text = str(payload.get("text") or "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="指令为空")
        session = registry.get(ctx.user_id, None, ctx.user_name, ctx.is_admin, ctx.role)
        result = await registry.submit(session, text)
        result["session"] = {"user_id": ctx.user_id}
        return result

    @router.post("/api/cancel", dependencies=[csrf])
    async def cancel(ctx: ToolContextData = Depends(member_context)) -> Dict[str, Any]:
        session = registry.get(ctx.user_id, None, ctx.user_name, ctx.is_admin, ctx.role)
        await registry.cancel(session)
        return {"ok": True}

    # ------------------------------------------------------------ 原生网页玩法
    @router.get("/api/game/world")
    async def game_world_state(ctx: ToolContextData = Depends(member_context)) -> Dict[str, Any]:
        data = await game_world.world(ctx.user_id)
        session = registry.get(ctx.user_id, None, ctx.user_name, ctx.is_admin, ctx.role)
        data["identity"] = {"is_admin": ctx.is_admin}
        data["session"] = registry.status(session, "", len(session.transport.outbox))
        return data

    @router.get("/api/game/sprite/{pokemon_id}")
    async def game_sprite(
        pokemon_id: str,
        _ctx: ToolContextData = Depends(member_context),
    ) -> Response:
        pid = resolve_pokemon(pokemon_id)
        if not pid:
            raise HTTPException(status_code=404, detail="没有找到该宝可梦")
        return _sprite_response(_sprite_path(pid), pid)

    @router.post("/api/game/action", dependencies=[csrf])
    async def game_action(
        payload: GameActionPayload,
        ctx: ToolContextData = Depends(member_context),
    ) -> Response:
        session = registry.get(ctx.user_id, None, ctx.user_name, ctx.is_admin, ctx.role)
        try:
            result = await registry.act(
                session,
                payload.action,
                payload.value,
                payload.operation,
                payload.offset,
            )
        except ActionError as exc:
            snapshot = registry.status(session, session.operation, 0)
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    **snapshot,
                    "ok": False,
                    "error": exc.message,
                    "stale": False,
                    "action": payload.action,
                    "session": {"user_id": ctx.user_id},
                },
            )
        status_code = 409 if result.get("stale") else 200
        result["action"] = (result.get("last_action") or {}).get("action") or payload.action
        result["session"] = {"user_id": ctx.user_id}
        if status_code != 200:
            return JSONResponse(status_code=status_code, content=result)
        return result

    # ----------------------------------------------------------------- 管理
    @router.get("/api/admin/state")
    async def admin_state(ctx: ToolContextData = Depends(admin_context)) -> Dict[str, Any]:
        from ..compat.aps import scheduler
        from ..llm.integration import _REGISTERED
        from ..paths import data_root, pokemon_data_dir

        icon_dir = pokemon_data_dir() / "resource" / "icon"
        star_dir = pokemon_data_dir() / "resource" / "staricon"
        overview = await analytics.global_overview()
        return {
            "ok": True,
            "version": VERSION,
            "data_dir": str(data_root()),
            "icons": len(list(icon_dir.glob("*.png"))) if icon_dir.exists() else 0,
            "star_icons": len(list(star_dir.glob("*.png"))) if star_dir.exists() else 0,
            "menu_entries": len(build_entries()),
            "tools_registered": bool(_REGISTERED),
            "tools_count": len(TOOLS),
            "scheduler_jobs": [job.name for job in scheduler.jobs],
            "players": overview["players"],
            "pokemon_records": overview["pokemon_records"],
            "web_sessions": len(registry._sessions),
        }

    @router.post("/api/admin/resource/download", dependencies=[csrf])
    async def admin_download_resources(
        ctx: ToolContextData = Depends(admin_context),
    ) -> Dict[str, Any]:
        import asyncio

        from ..resources.downloader import download_all

        task = asyncio.create_task(download_all())

        def _log(fut):
            try:
                logger.info(f"[pokemon] 素材全量下载: {fut.result()}")
            except Exception as exc:
                logger.warning(f"[pokemon] 素材全量下载失败: {exc}")

        task.add_done_callback(_log)
        return {"ok": True, "accepted": True}

    @router.post("/api/admin/reload", dependencies=[csrf])
    async def admin_reload(ctx: ToolContextData = Depends(admin_context)) -> Dict[str, Any]:
        from ..llm.integration import setup_llm_tools
        from ..menu import write_external_menu

        path = write_external_menu()
        registered = setup_llm_tools()
        return {"ok": True, "external_menu": str(path), "tools_registered": registered}

    # ----------------------------------------------------------------- 页面
    @router.get("/static/app.js", include_in_schema=False)
    async def page_script(_ctx: ToolContextData = Depends(member_context)) -> FileResponse:
        return _asset_response("app.js", "application/javascript")

    @router.get("/static/qweb-theme.js", include_in_schema=False)
    async def qweb_theme_script(_ctx: ToolContextData = Depends(member_context)) -> FileResponse:
        return _asset_response("qweb-theme.js", "application/javascript")

    @router.get("/static/game.css", include_in_schema=False)
    async def game_stylesheet(_ctx: ToolContextData = Depends(member_context)) -> FileResponse:
        return _asset_response("game.css", "text/css")

    @router.get("/static/trainer.png", include_in_schema=False)
    async def trainer_sprite(_ctx: ToolContextData = Depends(member_context)) -> FileResponse:
        file = STATIC_DIR.parents[1] / "Pokemon/pokemon_duel/texture2D/trainers/背包客.png"
        return FileResponse(file, media_type="image/png")

    @router.get("/static/game.js", include_in_schema=False)
    async def game_script(_ctx: ToolContextData = Depends(member_context)) -> FileResponse:
        return _asset_response("game.js", "application/javascript")

    @router.get("", response_class=HTMLResponse)
    @router.get("/", response_class=HTMLResponse)
    async def index(
        request: Request,
        _ctx: ToolContextData = Depends(member_context),
    ) -> HTMLResponse:
        file = STATIC_DIR / "index.html"
        if not file.exists():
            return HTMLResponse("<h1>宝可梦网页资源缺失</h1>", status_code=500)
        html = file.read_text(encoding="utf-8")
        base = request.url.path.rstrip("/") or ""
        html = html.replace("__POKEMON_BASE__", base)
        headers = {
            "X-Frame-Options": "SAMEORIGIN",
            "Cache-Control": "private, no-store",
            "Content-Security-Policy": (
                "default-src 'self'; base-uri 'self'; object-src 'none'; form-action 'self'; "
                "script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
                "frame-ancestors 'self'"
            ),
        }
        return HTMLResponse(html, headers=headers)

    return router


# 默认路由使用真实宿主依赖；没有宿主时三个依赖都会返回 503，不会回退游客。
router = create_router(load_host_auth() or unavailable_auth())

_MOUNTED: Set[Tuple[int, str]] = set()


def setup_web(app: Any = None, auth: Optional[AuthDependencies] = None, *, force: bool = False) -> bool:
    """挂载 QWeb 路由。

    默认从 ``src.qi_web.dependencies`` 读取依赖。网页默认关闭；离线测试可显式
    传入 ``auth=AuthDependencies(...)`` 并设置 ``POKEMON_WEB_ENABLED=true`` 或
    使用 ``force=True``。找不到宿主依赖时不挂载，也不创建游客入口。
    """

    if not plugin_config.pokemon_web_enabled and not force:
        logger.debug("[pokemon] 网页默认关闭（POKEMON_WEB_ENABLED=false），跳过挂载")
        return False
    if not plugin_config.pokemon_qweb_enabled:
        logger.debug("[pokemon] QWeb 入口关闭，跳过挂载")
        return False

    auth = auth or load_host_auth()
    if auth is None:
        logger.warning(
            "[pokemon] 未找到 QWeb 宿主认证依赖 src.qi_web.dependencies，"
            "网页不挂载（禁止游客/假身份回退）"
        )
        return False

    if app is None:
        try:
            from nonebot import get_app

            app = get_app()
        except Exception as exc:
            logger.warning(f"[pokemon] 当前驱动器不支持 FastAPI，跳过网页模块: {exc}")
            return False

    member_prefix = plugin_config.pokemon_qweb_path.rstrip("/")
    admin_prefix = plugin_config.pokemon_qweb_admin_path.rstrip("/")
    mount_plan: list[Tuple[str, bool]] = []
    if member_prefix and member_prefix == admin_prefix:
        mount_plan.append((member_prefix, True))
    else:
        if member_prefix:
            mount_plan.append((member_prefix, False))
        if admin_prefix:
            mount_plan.append((admin_prefix, True))

    # 公网由 QWeb 的 API 前缀反代，页面、脚本与业务请求共用身份校验。
    if member_prefix and member_prefix != admin_prefix:
        mount_plan.append(("/qweb/api/v1/plugins/pokemon", False))
    if admin_prefix:
        mount_plan.append(("/qweb/api/v1/plugins/admin/pokemon", True))

    mounted: list[str] = []
    for prefix, admin_only in mount_plan:
        key = (id(app), prefix)
        if key in _MOUNTED:
            continue
        built = create_router(auth, admin_only=admin_only)
        try:
            from src.qi_web.plugin_pages import include_plugin_router
        except ImportError:
            app.include_router(built, prefix=prefix, tags=["pokemon"])
        else:
            include_plugin_router(app, built, prefix=prefix, tags=["pokemon"])
        _MOUNTED.add(key)
        mounted.append(prefix)
    if mounted:
        logger.info(f"[pokemon] QWeb 网页入口已挂载: {', '.join(mounted)}")
    return bool(mounted)


__all__ = [
    "account_context",
    "create_router",
    "router",
    "setup_web",
]

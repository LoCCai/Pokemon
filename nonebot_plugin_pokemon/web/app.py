"""网页 / QWeb API 与页面路由。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import unquote

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from ..compat.logger import logger
from ..config import plugin_config
from ..game import analytics, charts, repository
from ..game.data import dex_entry, item_entry, move_entry
from ..llm.agent import run_agent
from ..llm.tools import ToolContextData
from ..menu import PLUGIN_ID, VERSION, external_menu, help_cards
from ..menu.catalog import build_entries, category_index, search_entries as search_menu
from ..paths import STATIC_DIR
from .session import registry


def _truthy(value: Optional[str]) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "admin"}


def identity(request: Request) -> ToolContextData:
    headers = request.headers
    user_id = (
        headers.get(plugin_config.pokemon_qweb_user_header)
        or headers.get("X-Pokemon-User")
        or request.query_params.get("user_id")
        or request.cookies.get("pokemon_uid")
    )
    user_name = (
        headers.get(plugin_config.pokemon_qweb_name_header)
        or headers.get("X-Pokemon-User-Name")
        or request.query_params.get("user_name")
        or "网页玩家"
    )
    user_name = unquote(str(user_name))
    is_admin = _truthy(headers.get(plugin_config.pokemon_qweb_admin_header)) or _truthy(
        headers.get("X-Pokemon-Is-Admin")
    )
    secret = plugin_config.pokemon_qweb_secret
    qweb = request.url.path.startswith(
        (plugin_config.pokemon_qweb_path, plugin_config.pokemon_qweb_admin_path)
    )
    if qweb and secret:
        supplied = headers.get("X-QWeb-Secret", "")
        if supplied != secret:
            raise HTTPException(status_code=401, detail="QWeb 认证失败")
    if not user_id:
        if not plugin_config.pokemon_web_allow_guest:
            raise HTTPException(status_code=401, detail="缺少用户身份")
        user_id = plugin_config.pokemon_web_default_user
    if not is_admin:
        try:
            from nonebot import get_driver

            if str(user_id) in {str(x) for x in get_driver().config.superusers}:
                is_admin = True
        except Exception:
            pass
    return ToolContextData(
        user_id=str(user_id),
        group_id=request.query_params.get("group_id"),
        user_name=str(user_name),
        is_admin=is_admin,
        platform="web",
    )


router = APIRouter(dependencies=[Depends(identity)])


@router.get("/api/health")
async def health() -> Dict[str, Any]:
    return {"ok": True, "plugin": PLUGIN_ID, "version": VERSION}


@router.get("/api/catalog")
async def catalog() -> Dict[str, Any]:
    return {
        "plugin_id": PLUGIN_ID,
        "name": "宝可梦",
        "version": VERSION,
        "description": "宝可梦养成、探索、对战、道具与小游戏",
        "menu_data": build_entries(),
        "external_menu": external_menu(),
    }


@router.get("/api/menu")
async def menu(q: str = Query(default="")) -> Dict[str, Any]:
    entries = search_menu(q) if q else build_entries()
    return {
        "categories": category_index(entries),
        "cards": help_cards(),
        "total": len(entries),
    }


@router.get("/api/bootstrap")
async def bootstrap(request: Request) -> Dict[str, Any]:
    ctx = identity(request)
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
        "llm": {
            "enabled": bool(plugin_config.pokemon_llm_enabled),
            "configured": _llm_configured(),
        },
        "version": VERSION,
    }


def _llm_configured() -> bool:
    try:
        from ..llm.agent import resolve_endpoint

        return resolve_endpoint() is not None
    except Exception:
        return False


@router.get("/api/player")
async def player(request: Request, uid: str = Query(default="")) -> Dict[str, Any]:
    ctx = identity(request)
    target = uid if uid and ctx.is_admin else ctx.user_id
    profile = await repository.profile(target)
    owned = await repository.owned(target, 0)
    return {"profile": profile, "owned": owned}


@router.get("/api/pokedex")
async def pokedex(name: str = Query(default=""), q: str = Query(default="")) -> Dict[str, Any]:
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
async def move(name: str = Query(...)) -> Dict[str, Any]:
    data = move_entry(name)
    if not data:
        raise HTTPException(status_code=404, detail="没有找到该技能")
    return {"entry": data}


@router.get("/api/item")
async def item(name: str = Query(...)) -> Dict[str, Any]:
    data = item_entry(name)
    if not data:
        raise HTTPException(status_code=404, detail="没有找到该道具")
    return {"entry": data}


@router.get("/api/analytics/overview")
async def overview() -> Dict[str, Any]:
    return await analytics.global_overview()


@router.get("/api/leaderboard/{kind}")
async def leaderboard(kind: str) -> Dict[str, Any]:
    if kind == "dungeon":
        items = await repository.dungeon_leaderboard()
    elif kind == "pokedex":
        items = await repository.pokedex_leaderboard()
    else:
        items = await repository.score_leaderboard()
    return {"kind": kind, "items": items}


@router.get("/api/charts/{kind}")
async def chart(kind: str, request: Request, uid: str = Query(default="")) -> Response:
    ctx = identity(request)
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


@router.post("/api/command")
async def command(request: Request, payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    ctx = identity(request)
    text = str(payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="指令为空")
    session = registry.get(ctx.user_id, ctx.group_id, ctx.user_name, ctx.is_admin)
    result = await registry.submit(session, text)
    result["session"] = {"user_id": ctx.user_id, "group_id": ctx.group_id}
    return result


@router.post("/api/cancel")
async def cancel(request: Request) -> Dict[str, Any]:
    ctx = identity(request)
    session = registry.get(ctx.user_id, ctx.group_id, ctx.user_name, ctx.is_admin)
    await registry.cancel(session)
    return {"ok": True}


# --------------------------------------------------------------------- QWeb 管理
@router.get("/api/admin/state")
async def admin_state(request: Request) -> Dict[str, Any]:
    ctx = identity(request)
    if not ctx.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员身份")
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
        "scheduler_jobs": [job.name for job in scheduler.jobs],
        "players": overview["players"],
        "pokemon_records": overview["pokemon_records"],
        "web_sessions": len(registry._sessions),
    }


@router.post("/api/admin/resource/download")
async def admin_download_resources(request: Request) -> Dict[str, Any]:
    ctx = identity(request)
    if not ctx.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员身份")
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


@router.post("/api/admin/reload")
async def admin_reload(request: Request) -> Dict[str, Any]:
    ctx = identity(request)
    if not ctx.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员身份")
    from ..llm.integration import setup_llm_tools
    from ..menu import write_external_menu

    path = write_external_menu()
    registered = setup_llm_tools()
    return {"ok": True, "external_menu": str(path), "tools_registered": registered}


@router.post("/api/ai/chat")
async def ai_chat(request: Request, payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    ctx = identity(request)
    message = str(payload.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="消息为空")
    history = payload.get("history")
    if not isinstance(history, list):
        history = []
    reply = await run_agent(message, ctx, history)
    return reply.to_dict()


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    file = STATIC_DIR / "index.html"
    if not file.exists():
        return HTMLResponse("<h1>宝可梦网页资源缺失</h1>", status_code=500)
    html = file.read_text(encoding="utf-8")
    base = request.url.path.rstrip("/") or ""
    html = html.replace("__POKEMON_BASE__", base)
    html = html.replace("__POKEMON_QWEB_BASE__", plugin_config.pokemon_qweb_path.rstrip("/"))
    return HTMLResponse(html)


def setup_web() -> None:
    if not plugin_config.pokemon_web_enabled:
        return
    try:
        from nonebot import get_app

        app = get_app()
    except Exception as exc:
        logger.warning(f"[pokemon] 当前驱动器不支持 FastAPI，跳过网页模块: {exc}")
        return

    mounted: set[str] = set()
    prefixes = {plugin_config.pokemon_web_path.rstrip("/")}
    if plugin_config.pokemon_qweb_enabled:
        prefixes.add(plugin_config.pokemon_qweb_path.rstrip("/"))
        prefixes.add(plugin_config.pokemon_qweb_admin_path.rstrip("/"))
    for prefix in prefixes:
        if not prefix or prefix in mounted:
            continue
        mounted.add(prefix)
        app.include_router(router, prefix=prefix, tags=["pokemon"])
    logger.info(f"[pokemon] 网页入口已挂载: {', '.join(sorted(mounted))}")


__all__ = ["identity", "router", "setup_web"]

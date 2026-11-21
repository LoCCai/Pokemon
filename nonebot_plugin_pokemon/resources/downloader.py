"""素材下载器。

上游通过 gsuid_core 的资源镜像分发宝可梦图标（约 1100 张，74MB）。这里提供：

* **懒下载**：首次打开缺失图标时排队后台下载，当前请求先用占位图，不阻塞；
* **全量下载**：``pm下载全部资源`` 指令 / Web 设置页触发；
* **断点友好**：已存在且非空的文件跳过，写入使用 ``.part`` 原子替换。
"""

from __future__ import annotations

import asyncio
import re
import urllib.parse
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ..compat.logger import logger
from ..paths import pokemon_data_dir

_ICON_DIR_NAME = ("resource", "icon")
_STAR_DIR_NAME = ("resource", "staricon")

_pending: Optional["asyncio.Queue[Path]"] = None
_queued: set[str] = set()
_worker_task: Optional[asyncio.Task] = None


def _queue() -> "asyncio.Queue[Path]":
    global _pending
    if _pending is None:
        _pending = asyncio.Queue(maxsize=4096)
    return _pending


def resource_base_url() -> str:
    try:
        from ..config import plugin_config

        configured = (plugin_config.pokemon_resource_base_url or "").strip()
        if configured:
            return configured.rstrip("/")
    except Exception:
        pass
    import os

    return os.getenv("POKEMON_RESOURCE_BASE_URL", "https://silverwing.elysia.beauty/Pokemon").rstrip("/")


def _local_root() -> Path:
    return pokemon_data_dir()


def _remote_for(path: Path) -> Optional[str]:
    try:
        relative = path.resolve().relative_to(_local_root().resolve())
    except ValueError:
        return None
    if not relative.parts:
        return None
    quoted = "/".join(urllib.parse.quote(part) for part in relative.parts)
    return f"{resource_base_url()}/{quoted}"


def _auto_download() -> bool:
    try:
        from ..config import plugin_config

        return bool(plugin_config.pokemon_resource_auto_download)
    except Exception:
        return True


async def _fetch(url: str, timeout: float = 40.0) -> bytes:
    try:
        import httpx

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content
    except ImportError:  # pragma: no cover - httpx 是 NoneBot2 依赖
        import urllib.request

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: urllib.request.urlopen(url, timeout=timeout).read())


async def _download_one(path: Path, semaphore: asyncio.Semaphore) -> bool:
    remote = _remote_for(path)
    if remote is None or path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    async with semaphore:
        for attempt in range(2):
            try:
                data = await _fetch(remote)
                if not data:
                    return False
                tmp = path.with_suffix(path.suffix + ".part")
                tmp.write_bytes(data)
                tmp.replace(path)
                return True
            except Exception as exc:
                if attempt == 1:
                    logger.debug(f"[pokemon] 素材下载失败 {remote}: {exc}")
    return False


def _concurrency(default: int = 8) -> int:
    try:
        from ..config import plugin_config

        return max(1, min(32, int(plugin_config.pokemon_resource_download_concurrency or default)))
    except Exception:
        return default


async def _worker() -> None:
    semaphore = asyncio.Semaphore(_concurrency(6))
    tasks: set[asyncio.Task] = set()
    while True:
        path = await _queue().get()
        _queued.discard(str(path))
        task = asyncio.create_task(_download_one(path, semaphore))
        tasks.add(task)
        task.add_done_callback(tasks.discard)
        if len(tasks) > 24:
            await asyncio.gather(*list(tasks), return_exceptions=True)


def start_worker() -> None:
    global _worker_task
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    if _worker_task is None or _worker_task.done():
        _worker_task = loop.create_task(_worker())


def enqueue_missing(path: Path) -> None:
    if not _auto_download():
        return
    path = Path(path)
    if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        return
    key = str(path)
    if key in _queued:
        return
    try:
        _queued.add(key)
        _queue().put_nowait(path)
        start_worker()
    except asyncio.QueueFull:
        _queued.discard(key)


_INDEX_ENTRY = re.compile(
    r'<a href="([^"]+\.(?:png|jpg|jpeg|webp))">.*?</a>\s+(?:\S+\s+){2}(\d+)',
    re.S | re.I,
)


def parse_index(html: str) -> List[Tuple[str, int]]:
    entries: List[Tuple[str, int]] = []
    for href, size in _INDEX_ENTRY.findall(html):
        href = href.strip()
        if not href.endswith((".png", ".jpg", ".jpeg", ".webp")):
            continue
        try:
            entries.append((urllib.parse.unquote(href), int(size)))
        except ValueError:
            continue
    return entries


async def download_all(progress: Optional[Any] = None) -> str:
    """下载全部图标素材，返回面向用户的摘要。"""

    semaphore = asyncio.Semaphore(_concurrency(8))
    total = 0
    downloaded = 0
    failed = 0
    for relative, target in (
        ("resource/icon", _local_root() / "resource" / "icon"),
        ("resource/staricon", _local_root() / "resource" / "staricon"),
    ):
        url = f"{resource_base_url()}/{relative}/"
        try:
            html = (await _fetch(url, timeout=60)).decode("utf-8", "ignore")
        except Exception as exc:
            logger.warning(f"[pokemon] 读取素材目录失败 {url}: {exc}")
            continue
        entries = parse_index(html)
        target.mkdir(parents=True, exist_ok=True)
        pending: List[Path] = []
        for name, size in entries:
            total += 1
            path = target / name
            if path.exists() and path.stat().st_size == size:
                continue
            pending.append(path)
        results = await asyncio.gather(
            *(_download_one(path, semaphore) for path in pending),
            return_exceptions=True,
        )
        for result in results:
            if result is True:
                downloaded += 1
            elif isinstance(result, Exception):
                failed += 1
        if progress:
            try:
                await progress(relative, len(pending), downloaded)
            except Exception:
                pass

    return (
        f"素材下载完成：索引 {total} 个，新增 {downloaded} 个"
        + (f"，失败 {failed} 个" if failed else "")
    )


__all__ = ["download_all", "enqueue_missing", "parse_index", "resource_base_url", "start_worker"]

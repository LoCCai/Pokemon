"""轻量 cron 调度器（兼容 gsuid_core.aps.scheduler）。

只实现 Pokemon 插件实际使用的 cron 子集：``hour``、``minute``、``second``、
``day_of_week``、``day``、``month``，支持 ``*`` 与逗号列表。没有引入
APScheduler 依赖，插件开箱即用；需要更复杂调度时可在宿主侧替换。
"""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .logger import logger


def _match_field(value: int, expr: Any) -> bool:
    if expr is None:
        return True
    text = str(expr).strip()
    if text in {"", "*"}:
        return True
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            try:
                start, end = part.split("-", 1)
                if int(start) <= value <= int(end):
                    return True
            except ValueError:
                continue
        elif part.isdigit() and int(part) == value:
            return True
    return False


@dataclass
class _Job:
    func: Callable
    kwargs: Dict[str, Any]
    trigger: str = "cron"
    last_key: Optional[str] = None
    name: str = ""


class _Scheduler:
    def __init__(self) -> None:
        self.jobs: List[_Job] = []
        self._task: Optional[asyncio.Task] = None
        self._running = False

    def scheduled_job(self, trigger: str = "cron", **kwargs: Any) -> Callable:
        def decorator(func: Callable) -> Callable:
            self.jobs.append(
                _Job(
                    func=func,
                    kwargs=kwargs,
                    trigger=trigger,
                    name=f"{func.__module__}.{func.__name__}",
                )
            )
            return func

        return decorator

    # 兼容 APScheduler 写法（本项目暂未使用）
    def add_job(self, func: Callable, trigger: str = "cron", **kwargs: Any) -> None:
        self.jobs.append(_Job(func=func, kwargs=kwargs, trigger=trigger))

    def _due(self, job: _Job, now: datetime) -> bool:
        if job.kwargs.get("trigger", job.trigger) not in {"cron", None, ""}:
            return False
        if not _match_field(now.month, job.kwargs.get("month")):
            return False
        if not _match_field(now.day, job.kwargs.get("day")):
            return False
        # APScheduler: 0=周一 ... 6=周日；Python: 0=周一 ... 6=周日，一致
        if not _match_field(now.weekday(), job.kwargs.get("day_of_week")):
            return False
        if not _match_field(now.hour, job.kwargs.get("hour")):
            return False
        if not _match_field(now.minute, job.kwargs.get("minute")):
            return False
        second = job.kwargs.get("second")
        if second is not None and now.second > 10:
            return False
        return True

    async def _loop(self) -> None:
        while self._running:
            now = datetime.now()
            key = now.strftime("%Y%m%d%H%M")
            for job in list(self.jobs):
                try:
                    if job.last_key == key or not self._due(job, now):
                        continue
                    job.last_key = key
                    result = job.func()
                    if inspect.isawaitable(result):
                        asyncio.create_task(result)
                except Exception as exc:  # pragma: no cover - 调度任务防御
                    logger.warning(f"[pokemon] 定时任务 {job.name} 执行失败: {exc}")
            await asyncio.sleep(5)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        try:
            self._task = asyncio.create_task(self._loop())
        except RuntimeError:  # 没有运行中的事件循环
            self._running = False

    async def shutdown(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None


scheduler = _Scheduler()

__all__ = ["scheduler"]

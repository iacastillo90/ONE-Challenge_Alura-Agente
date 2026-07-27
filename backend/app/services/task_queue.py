from __future__ import annotations

from typing import Any

from arq import create_pool
from arq.connections import RedisSettings
from arq.jobs import Job
from loguru import logger

from app.core.config import settings


class TaskQueueFacade:
    def __init__(self) -> None:
        self._pool: Any = None

    async def start(self) -> None:
        rs = RedisSettings.from_dsn(settings.redis_url)
        self._pool = await create_pool(rs)
        logger.info(f"ARQ task queue connected to Redis at {settings.redis_url}")

    async def stop(self) -> None:
        if self._pool is not None:
            await self._pool.close(wait_for_jobs=True)
            self._pool = None
            logger.info("ARQ task queue stopped")

    async def enqueue(self, name: str, **kwargs: Any) -> str:
        job = await Job(name, **kwargs).enqueue(self._pool)
        logger.debug(f"ARQ job enqueued: {name} ({job.job_id[:8]}...)")
        return job.job_id

    @property
    def pool(self) -> Any:
        return self._pool

    async def check_health(self) -> bool:
        if self._pool is None:
            return False
        try:
            info = await self._pool.info("server")
            return info.get("redis_version", "") != ""
        except Exception:
            return False


_task_queue: TaskQueueFacade | None = None


def get_task_queue() -> TaskQueueFacade:
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueueFacade()
    return _task_queue

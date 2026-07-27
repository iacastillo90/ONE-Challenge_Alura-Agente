from __future__ import annotations

from arq.connections import RedisSettings
from loguru import logger

from app.core.config import settings
from app.services.tasks import cleanup_old_sessions, process_document


async def startup(ctx: dict) -> None:
    from app.core.database import init_db
    from app.core.logging import setup_json_logging

    setup_json_logging()
    await init_db()
    logger.info("ARQ worker started — DB initialized")


async def shutdown(ctx: dict) -> None:
    logger.info("ARQ worker shutting down")


WorkerSettings = {
    "functions": [process_document, cleanup_old_sessions],
    "redis_settings": RedisSettings.from_dsn(settings.redis_url),
    "on_startup": startup,
    "on_shutdown": shutdown,
    "keep_result": 3600,
    "keep_result_failed": 86400,
    "max_jobs": 4,
    "job_timeout": 600,
}

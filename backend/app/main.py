import asyncio
import secrets
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.middleware.metrics import PrometheusMiddleware, metrics_endpoint
from app.api.middleware.rate_limit_redis import RedisRateLimiter
from app.api.routes import auth, chat, documents, experiments, feedback, health, providers, sessions, webhooks
from app.core.auth import verify_jwt
from app.core.config import settings
from app.core.database import close_db, init_db
from app.core.exceptions import AppException, generic_exception_handler, global_exception_handler
from app.core.health import health_registry
from app.core.logging import setup_json_logging
from app.core.otel import setup_otel, shutdown_otel
from app.core.tracing import RequestLogMiddleware
from app.services.task_queue import get_task_queue


_background_tasks: list[asyncio.Task] = []


async def _run_cleanup():
    from app.services.tasks import cleanup_old_sessions

    while True:
        await asyncio.sleep(3600)
        try:
            await cleanup_old_sessions({})
            logger.debug("Limpieza programada: sesiones antiguas purgadas correctamente")
        except Exception as exc:
            logger.warning(f"La limpieza programada falló: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_json_logging()
    logger.info(f"Iniciando el backend del agente — nivel_log={settings.log_level}")
    await init_db()
    logger.info("Base de datos inicializada correctamente")

    otel_enabled = setup_otel(app)
    if otel_enabled:
        logger.info("Trazado con OpenTelemetry activado")

    q = get_task_queue()
    await q.start()

    _register_health_checks()

    _background_tasks.append(asyncio.create_task(_run_cleanup()))
    logger.info("Limpieza en segundo plano de sesiones programada (cada 3600s)")

    yield

    for t in _background_tasks:
        t.cancel()
    await asyncio.gather(*_background_tasks, return_exceptions=True)
    _background_tasks.clear()

    await q.stop()
    shutdown_otel()
    await close_db()
    logger.info("Cerrando el backend del agente")


def _register_health_checks():
    from app.core.database import engine
    from sqlalchemy import text

    async def _db_check():
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True

    async def _queue_check():
        q = get_task_queue()
        return await q.check_health()

    health_registry.register("database", _db_check)
    health_registry.register("task_queue", _queue_check)


app = FastAPI(
    title="ONE AI Agent",
    description="Agente inteligente con RAG, multi-provider LLM y orquestación",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-Request-ID"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.parsed_allowed_hosts,
)

app.add_middleware(RequestLogMiddleware)
app.add_middleware(PrometheusMiddleware)
app.add_middleware(RedisRateLimiter)


async def add_security_headers(request, call_next):
    nonce = secrets.token_urlsafe(16)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        f"default-src 'self'; "
        f"script-src 'self' 'nonce-{nonce}' 'strict-dynamic'; "
        f"style-src 'self' 'nonce-{nonce}'; "
        f"img-src 'self' data:; "
        f"connect-src 'self'; "
        f"frame-ancestors 'none'"
    )
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    response.headers["Content-Security-Policy-Nonce"] = nonce
    return response


app.add_middleware(BaseHTTPMiddleware, dispatch=add_security_headers)

app.add_exception_handler(AppException, global_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

app.add_route("/metrics", metrics_endpoint, include_in_schema=False)
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(health.router, tags=["health"])
app.include_router(
    chat.router,
    prefix="/chat",
    tags=["chat"],
    dependencies=[Depends(verify_jwt)],
)
app.include_router(
    documents.router,
    prefix="/documents",
    tags=["documents"],
    dependencies=[Depends(verify_jwt)],
)
app.include_router(
    providers.router,
    prefix="/providers",
    tags=["providers"],
    dependencies=[Depends(verify_jwt)],
)
app.include_router(
    sessions.router,
    prefix="/sessions",
    tags=["sessions"],
    dependencies=[Depends(verify_jwt)],
)
app.include_router(
    feedback.router,
    prefix="/feedback",
    tags=["feedback"],
    dependencies=[Depends(verify_jwt)],
)
app.include_router(
    experiments.router,
    prefix="/experiments",
    tags=["experiments"],
    dependencies=[Depends(verify_jwt)],
)
# Los webhooks usan su propia autenticación (secreto compartido para n8n;
# JWT solo en el endpoint /whatsapp/send expuesto a la plataforma).
app.include_router(
    webhooks.router,
    prefix="/webhooks",
    tags=["webhooks"],
)

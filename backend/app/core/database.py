import asyncio
import os

from loguru import logger
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

RETRY_MAX_ATTEMPTS = 5
RETRY_BASE_DELAY = 0.5
RETRY_MAX_DELAY = 10.0

engine = create_async_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False,
)

async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _retry_delay(attempt: int) -> float:
    delay = min(RETRY_BASE_DELAY * (2 ** (attempt - 1)), RETRY_MAX_DELAY)
    jitter = delay * 0.1
    return delay + jitter


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def _execute_with_retry(coro_factory, description: str = "db operation"):
    last_error = None
    for attempt in range(1, RETRY_MAX_ATTEMPTS + 1):
        try:
            return await coro_factory()
        except OperationalError as e:
            last_error = e
            if attempt < RETRY_MAX_ATTEMPTS:
                delay = _retry_delay(attempt)
                logger.warning(f"DB {description} failed (attempt {attempt}/{RETRY_MAX_ATTEMPTS}): {e}")
                logger.info(f"Retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)
            else:
                logger.critical(f"DB {description} failed after {RETRY_MAX_ATTEMPTS} attempts: {e}")
                raise
        except Exception as e:
            last_error = e
            raise
    raise last_error


async def init_db():
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config(
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "alembic.ini")
    )

    # Clave de bloqueo consultivo (advisory-lock) compartida por cada proceso que pueda ejecutar migraciones
    # (cada worker de uvicorn + cada worker de ARQ). Solo uno ejecuta la migración a la vez;
    # el resto espera a que finalice y luego ejecuta operaciones no-op idempotentes.
    MIGRATION_LOCK_KEY = 727_727_727

    async def _run_migrations():
        loop = asyncio.get_running_loop()

        # Mantiene un bloqueo consultivo a nivel de sesión durante toda la migración
        # para evitar carreras concurrentes entre workers al ejecutar alembic o CREATE INDEX.
        async with engine.connect() as lock_conn:
            await lock_conn.execute(
                text("SELECT pg_advisory_lock(:k)"), {"k": MIGRATION_LOCK_KEY}
            )
            try:
                async with engine.begin() as conn:
                    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))

                await loop.run_in_executor(None, command.upgrade, alembic_cfg, "head")

                # Los índices requieren que la tabla de embeddings exista (post-migración).
                async with engine.begin() as conn:
                    await conn.execute(
                        text(
                            "CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON embeddings "
                            "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
                        )
                    )
                    await conn.execute(
                        text(
                            "CREATE INDEX IF NOT EXISTS idx_embeddings_fts ON embeddings "
                            "USING gin (to_tsvector('spanish', content))"
                        )
                    )
            finally:
                await lock_conn.execute(
                    text("SELECT pg_advisory_unlock(:k)"), {"k": MIGRATION_LOCK_KEY}
                )

        logger.info("Database schema initialized (via Alembic)")

    await _execute_with_retry(_run_migrations, "init_db")

    await _verify_embedding_dimension()

    try:
        from app.core.auth import seed_admin_user
        admin_id = await seed_admin_user()
        logger.info(f"Admin user ready: {admin_id[:8]}...")
    except Exception as e:
        logger.warning(f"Could not seed admin user: {e}")

    try:
        from app.core.auth import seed_demo_user
        demo_id = await seed_demo_user()
        if demo_id:
            logger.info(f"Demo user ready: {demo_id[:8]}...")
    except Exception as e:
        logger.warning(f"Could not seed demo user: {e}")


async def _verify_embedding_dimension() -> None:
    """Fail loudly if the pgvector column dimension does not match the configured
    embedding dimension. For pgvector, ``atttypmod`` holds the vector dimension."""
    if settings.vector_store_type != "pgvector":
        return
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT atttypmod FROM pg_attribute "
                    "WHERE attrelid = 'embeddings'::regclass AND attname = 'embedding'"
                )
            )
            col_dim = result.scalar()
        if col_dim and col_dim > 0 and col_dim != settings.embedding_dimension:
            logger.critical(
                f"EMBEDDING DIMENSION MISMATCH: embeddings.embedding is vector({col_dim}) "
                f"but EMBEDDING_DIMENSION={settings.embedding_dimension}. "
                f"Inserts/searches will fail. Align EMBEDDING_DIMENSION with your embedding "
                f"model, or run a migration to change the column dimension."
            )
    except Exception as e:
        logger.debug(f"Embedding dimension check skipped: {e}")


async def close_db():
    await engine.dispose()
    logger.info("Database engine disposed")

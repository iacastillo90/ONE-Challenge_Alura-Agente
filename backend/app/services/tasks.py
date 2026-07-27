from __future__ import annotations

import os
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from loguru import logger

from app.core.database import async_session_factory
from app.core.models import ChatSessionRecord, DocumentRecord, UserRecord
from app.core.storage import get_storage_backend
from app.rag.ingestion.loader import DocumentLoader
from app.rag.ingestion.processor import IngestionProcessor
from app.rag.ingestion.splitter import RecursiveChunker

_worker_processor: IngestionProcessor | None = None


async def _ensure_processor() -> IngestionProcessor:
    global _worker_processor
    if _worker_processor is None:
        from app.core.dependencies import get_embedding_provider, get_vector_store

        embedding = await get_embedding_provider()
        store = await get_vector_store()
        _worker_processor = IngestionProcessor(
            loader=DocumentLoader(),
            splitter=RecursiveChunker(),
            embedding_provider=embedding,
            vector_store=store,
        )
    return _worker_processor


async def process_document(
    ctx: dict,
    *,
    doc_id: str,
    user_id: str,
    storage_key: str,
    ext: str,
    file_size: int,
    filename: str | None = None,
) -> None:
    from app.api.middleware.metrics import DOCUMENTS_CHUNKS, DOCUMENTS_UPLOADED

    logger.info(f"Worker processing document {doc_id[:8]}... for user {user_id[:8]}... ({file_size} bytes)")

    tmp_path: str | None = None
    try:
        processor = await _ensure_processor()

        async with async_session_factory() as session:
            user = await session.get(UserRecord, user_id)
            if user is None:
                raise ValueError(f"User {user_id} not found")

        # Fetch bytes through the storage backend (local disk or S3/MinIO) and
        # materialize a temp file so the loader can read it uniformly.
        storage = get_storage_backend()
        content = await storage.read(storage_key)
        fd, tmp_path = tempfile.mkstemp(suffix=ext or "")
        with os.fdopen(fd, "wb") as fh:
            fh.write(content)

        chunk_count = await processor.process(
            Path(tmp_path), doc_id, file_size, user_id=user_id, source_name=filename
        )

        async with async_session_factory() as session:
            doc = await session.get(DocumentRecord, doc_id)
            if doc is not None:
                doc.status = "ready"
                doc.chunks = chunk_count
                doc.updated_at = datetime.now(UTC)
                await session.commit()

        DOCUMENTS_UPLOADED.labels(status="completed").inc()
        DOCUMENTS_CHUNKS.observe(chunk_count)
        logger.info(f"Document {doc_id[:8]}... processed: {chunk_count} chunks")

    except Exception as exc:
        DOCUMENTS_UPLOADED.labels(status="error").inc()
        async with async_session_factory() as session:
            doc = await session.get(DocumentRecord, doc_id)
            if doc is not None:
                doc.status = "error"
                doc.error = str(exc)[:500]
                doc.updated_at = datetime.now(UTC)
                await session.commit()
        logger.error(f"Document {doc_id[:8]}... processing failed: {exc}")
        raise
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


SESSION_CLEANUP_INTERVAL = 3600
SESSION_MAX_AGE_DAYS = 30


async def cleanup_old_sessions(ctx: dict) -> None:
    cutoff = datetime.now(UTC) - timedelta(days=SESSION_MAX_AGE_DAYS)
    async with async_session_factory() as session:
        result = await session.execute(
            ChatSessionRecord.__table__.delete().where(
                ChatSessionRecord.updated_at < cutoff
            )
        )
        await session.commit()
        deleted = result.rowcount
        if deleted:
            logger.info(f"Cleaned up {deleted} stale sessions older than {SESSION_MAX_AGE_DAYS} days")

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import ClassVar

from loguru import logger
from sqlalchemy import select, func as sa_func

from app.api.middleware.metrics import DOCUMENTS_UPLOADED
from app.core.database import async_session_factory
from app.core.exceptions import DocumentNotFoundError, DocumentProcessingError
from app.core.models import DocumentRecord
from app.core.security import detect_secrets
from app.core.storage import get_storage_backend
from app.rag.vector_store.base import VectorStore
from app.services.task_queue import get_task_queue


class DocumentService:
    ALLOWED_EXTENSIONS: ClassVar[set[str]] = {".pdf", ".csv", ".txt", ".md"}

    def __init__(self, vector_store: VectorStore):
        self._vector_store = vector_store
        self._storage = get_storage_backend()

    async def upload(self, filename: str, content: bytes, user_id: str) -> dict:
        ext = Path(filename).suffix.lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise DocumentProcessingError(f"Formato no soportado: {ext}")

        try:
            text_content = content.decode("utf-8", errors="ignore")
            secret_findings = detect_secrets(text_content)
            for finding in secret_findings:
                logger.warning(f"Se detectó un secreto en el documento cargado {filename}: {finding}")
        except Exception:
            pass

        doc_id = str(uuid.uuid4())
        # Clave de almacenamiento relativa — funciona de forma uniforme para disco local y S3/MinIO.
        storage_key = f"documents/{user_id}/{doc_id}{ext}"
        await self._storage.save(storage_key, content)

        logger.info(f"Carga guardada: {filename} ({len(content)} bytes) para el usuario {user_id[:8]}...")

        now = datetime.now(timezone.utc)
        record = DocumentRecord(
            id=doc_id,
            user_id=user_id,
            filename=filename,
            status="processing",
            chunks=0,
            file_size=len(content),
            created_at=now,
            updated_at=now,
        )

        async with async_session_factory() as session:
            session.add(record)
            await session.commit()

        q = get_task_queue()
        await q.enqueue(
            "process_document",
            doc_id=doc_id,
            user_id=user_id,
            storage_key=storage_key,
            ext=ext,
            filename=filename,
            file_size=len(content),
        )

        DOCUMENTS_UPLOADED.labels(status="processing").inc()

        return await self._get_doc(doc_id, user_id)

    async def _get_doc(self, doc_id: str, user_id: str) -> dict:
        async with async_session_factory() as session:
            doc = await session.get(DocumentRecord, doc_id)
            if not doc or doc.user_id != user_id:
                raise DocumentNotFoundError(f"Documento no encontrado: {doc_id}")
            return {
                "id": doc.id,
                "filename": doc.filename,
                "status": doc.status,
                "chunks": doc.chunks,
                "file_size": doc.file_size,
                "created_at": doc.created_at.isoformat(),
                "error": doc.error,
            }

    async def delete(self, doc_id: str, user_id: str) -> None:
        for ext in self.ALLOWED_EXTENSIONS:
            p = f"documents/{user_id}/{doc_id}{ext}"
            try:
                await self._storage.delete(p)
            except Exception:
                pass

        await self._vector_store.delete_document(doc_id)

        async with async_session_factory() as session:
            doc = await session.get(DocumentRecord, doc_id)
            if not doc or doc.user_id != user_id:
                raise DocumentNotFoundError(f"Documento no encontrado: {doc_id}")
            await session.delete(doc)
            await session.commit()

        logger.info(f"Documento eliminado: {doc_id}")

    async def list_documents(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        async with async_session_factory() as session:
            count_q = select(sa_func.count(DocumentRecord.id)).where(
                DocumentRecord.user_id == user_id
            )
            total = (await session.execute(count_q)).scalar() or 0

            rows = await session.execute(
                select(DocumentRecord)
                .where(DocumentRecord.user_id == user_id)
                .order_by(DocumentRecord.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            docs = rows.scalars().all()
            return [
                {
                    "id": d.id,
                    "filename": d.filename,
                    "status": d.status,
                    "chunks": d.chunks,
                    "file_size": d.file_size,
                    "created_at": d.created_at.isoformat(),
                    "error": d.error,
                }
                for d in docs
            ], total

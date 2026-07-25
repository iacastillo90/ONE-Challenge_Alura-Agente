import uuid
from pathlib import Path
from datetime import datetime, timezone

from loguru import logger

from app.core.exceptions import DocumentNotFoundError, DocumentProcessingError
from app.rag.ingestion.loader import DocumentLoader
from app.rag.ingestion.processor import IngestionProcessor
from app.rag.vector_store.base import VectorStore

UPLOAD_DIR = Path("./uploads")
ALLOWED_EXTENSIONS = {".pdf", ".csv"}


class DocumentService:
    def __init__(self, processor: IngestionProcessor, vector_store: VectorStore):
        self._processor = processor
        self._vector_store = vector_store
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self._documents: dict[str, dict] = {}

    async def upload(self, filename: str, content: bytes) -> dict:
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise DocumentProcessingError(f"Formato no soportado: {ext}")

        doc_id = str(uuid.uuid4())
        file_path = UPLOAD_DIR / f"{doc_id}{ext}"
        file_path.write_bytes(content)

        logger.info(f"Saved upload: {file_path}")

        self._documents[doc_id] = {
            "id": doc_id,
            "filename": filename,
            "status": "processing",
            "chunks": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            chunk_count = await self._processor.process(file_path, doc_id)
            self._documents[doc_id]["status"] = "ready"
            self._documents[doc_id]["chunks"] = chunk_count
        except Exception as e:
            self._documents[doc_id]["status"] = "error"
            self._documents[doc_id]["error"] = str(e)
            logger.error(f"Document processing failed: {e}")

        return self._documents[doc_id]

    async def delete(self, doc_id: str) -> None:
        if doc_id not in self._documents:
            raise DocumentNotFoundError(f"Document not found: {doc_id}")

        await self._vector_store.delete_document(doc_id)

        file_path = UPLOAD_DIR / doc_id
        for ext in ALLOWED_EXTENSIONS:
            p = file_path.with_suffix(ext)
            if p.exists():
                p.unlink()
                break

        del self._documents[doc_id]
        logger.info(f"Deleted document: {doc_id}")

    async def list_documents(self) -> list[dict]:
        return [
            {
                "id": doc_id,
                "filename": info["filename"],
                "status": info["status"],
                "chunks": info["chunks"],
                "created_at": info["created_at"],
                "error": info.get("error"),
            }
            for doc_id, info in self._documents.items()
        ]

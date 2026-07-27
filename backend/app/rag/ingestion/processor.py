import time
from pathlib import Path

from loguru import logger

from app.core.config import settings
from app.core.security import assert_safe_content
from app.rag.embeddings.base import EmbeddingProvider
from app.rag.ingestion.loader import DocumentLoader
from app.rag.ingestion.splitter import RecursiveChunker
from app.rag.vector_store.base import VectorStore


class IngestionProcessor:
    MAX_CHUNKS = settings.max_chunks_per_document

    def __init__(
        self,
        loader: DocumentLoader,
        splitter: RecursiveChunker,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
    ):
        self._loader = loader
        self._splitter = splitter
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store

    async def process(
        self,
        file_path: str | Path,
        document_id: str,
        original_size: int = 0,
        user_id: str | None = None,
        source_name: str | None = None,
    ) -> int:
        start = time.perf_counter()
        file_path = Path(file_path)
        source = source_name or file_path.name
        logger.info(f"Processing document: {source} (id={document_id})")

        raw_text = await self._loader.load(file_path, original_size)
        logger.info(f"Extracted {len(raw_text)} chars from {source}")

        assert_safe_content(raw_text, context=f"document {source}")

        chunks = self._splitter.split_text(raw_text, source=source)

        if len(chunks) > self.MAX_CHUNKS:
            logger.warning(
                f"Truncating {len(chunks)} chunks to {self.MAX_CHUNKS} for {file_path.name}"
            )
            chunks = chunks[: self.MAX_CHUNKS]

        logger.info(f"Split into {len(chunks)} chunks")

        chunk_texts = [c.content for c in chunks]
        metadatas = [
            {**c.metadata, "document_id": document_id, "chunk_index": i, "user_id": user_id or ""}
            for i, c in enumerate(chunks)
        ]

        embeddings = await self._embedding_provider.embed_texts(chunk_texts)
        logger.info(f"Generated {len(embeddings)} embeddings")

        await self._vector_store.add_texts(chunk_texts, embeddings, metadatas)

        elapsed = time.perf_counter() - start
        logger.info(
            f"Document {file_path.name} processed in {elapsed:.2f}s — {len(chunks)} chunks"
        )

        return len(chunks)

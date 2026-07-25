import time
from pathlib import Path

from loguru import logger

from app.core.exceptions import DocumentProcessingError
from app.rag.embeddings.base import EmbeddingProvider
from app.rag.ingestion.loader import DocumentLoader
from app.rag.ingestion.splitter import SemanticChunker
from app.rag.vector_store.base import VectorStore


class IngestionProcessor:
    def __init__(
        self,
        loader: DocumentLoader,
        splitter: SemanticChunker,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
    ):
        self._loader = loader
        self._splitter = splitter
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store

    async def process(self, file_path: str | Path, document_id: str) -> int:
        start = time.perf_counter()
        file_path = Path(file_path)
        logger.info(f"Processing document: {file_path.name} (id={document_id})")

        raw_text = await self._loader.load(file_path)
        logger.info(f"Extracted {len(raw_text)} chars from {file_path.name}")

        chunks = self._splitter.split_text(raw_text, source=file_path.name)
        logger.info(f"Split into {len(chunks)} chunks")

        chunk_texts = [c.content for c in chunks]
        metadatas = [
            {**c.metadata, "document_id": document_id, "chunk_index": i}
            for i, c in enumerate(chunks)
        ]

        embeddings = await self._embedding_provider.embed_texts(chunk_texts)
        logger.info(f"Generated {len(embeddings)} embeddings")

        await self._vector_store.add_texts(chunk_texts, embeddings, metadatas)

        elapsed = time.perf_counter() - start
        logger.info(f"Document {file_path.name} processed in {elapsed:.2f}s — {len(chunks)} chunks")

        return len(chunks)

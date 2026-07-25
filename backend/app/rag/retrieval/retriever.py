from loguru import logger

from app.rag.embeddings.base import EmbeddingProvider
from app.rag.vector_store.base import Document, VectorStore


class Retriever:
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        top_k: int = 5,
        score_threshold: float = 0.0,
    ):
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store
        self._top_k = top_k
        self._score_threshold = score_threshold

    async def retrieve(self, query: str) -> list[Document]:
        logger.debug(f"Retrieving context for: {query[:50]}...")

        query_embedding = await self._embedding_provider.embed_query(query)

        results = await self._vector_store.similarity_search(
            query_embedding=query_embedding,
            k=self._top_k,
            score_threshold=self._score_threshold,
        )

        logger.debug(f"Retrieved {len(results)} relevant chunks")
        return results

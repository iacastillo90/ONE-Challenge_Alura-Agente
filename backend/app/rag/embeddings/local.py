import asyncio
from loguru import logger
from sentence_transformers import SentenceTransformer

from app.rag.embeddings.base import EmbeddingProvider


class LocalEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        logger.info(f"Loading embedding model: {model_name}")
        self._model = SentenceTransformer(model_name)
        self._dim = self._model.get_sentence_embedding_dimension()
        logger.info(f"Embedding model loaded — dim={self._dim}")

    def get_dimension(self) -> int:
        return self._dim

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        loop = asyncio.get_running_loop()
        embeddings = await loop.run_in_executor(
            None, lambda: self._model.encode(texts, show_progress_bar=False)
        )
        return embeddings.tolist()

    async def embed_query(self, query: str) -> list[float]:
        loop = asyncio.get_running_loop()
        embedding = await loop.run_in_executor(
            None, lambda: self._model.encode(query, show_progress_bar=False)
        )
        return embedding.tolist()

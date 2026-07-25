from loguru import logger
from sentence_transformers import SentenceTransformer

from app.rag.embeddings.base import EmbeddingProvider


class LocalEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        logger.info(f"Loading embedding model: {model_name}")
        self._model = SentenceTransformer(model_name)
        logger.info(f"Embedding model loaded — dim={self._model.get_sentence_embedding_dimension()}")

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        embeddings = self._model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()

    async def embed_query(self, query: str) -> list[float]:
        embedding = self._model.encode(query, show_progress_bar=False)
        return embedding.tolist()

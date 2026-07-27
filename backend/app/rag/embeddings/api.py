from loguru import logger

from app.core.config import settings
from app.rag.embeddings.base import EmbeddingProvider


class APIEmbeddingProvider(EmbeddingProvider):
    def __init__(self):
        self._dim = settings.embedding_dimension
        self._client = None
        if settings.gemini_api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=settings.gemini_api_key)
                logger.info("API embedding provider using Gemini")
            except Exception:
                pass
        if not self._client and settings.openai_compatible_api_key:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=settings.openai_compatible_api_key,
                base_url=settings.openai_compatible_base_url or "https://api.openai.com/v1",
            )
            logger.info("API embedding provider using OpenAI-compatible")

    def get_dimension(self) -> int:
        return self._dim

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not self._client:
            raise RuntimeError("No API embedding client configured")

        if hasattr(self._client, "models"):  # OpenAI-compatible
            resp = await self._client.embeddings.create(
                model=settings.embedding_model,
                input=texts,
            )
            return [e.embedding for e in resp.data]

        results = []
        for text in texts:
            result = await self._client.aio.models.embed_content(
                model=settings.embedding_model,
                contents=text,
            )
            results.append(result.embeddings[0].values)
        return results

    async def embed_query(self, query: str) -> list[float]:
        embeddings = await self.embed_texts([query])
        return embeddings[0]

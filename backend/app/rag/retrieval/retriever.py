import hashlib
import time

from loguru import logger
from opentelemetry import trace

from app.api.middleware.metrics import (
    RETRIEVAL_LATENCY,
    RETRIEVAL_QUERIES,
    RETRIEVAL_RESULTS,
    RETRIEVAL_SCORES,
)
from app.core.cache import rag_cache
from app.core.config import settings
from app.core.retrieval_config import DEFAULT_CONFIG, RetrievalConfig
from app.rag.embeddings.base import EmbeddingProvider
from app.rag.vector_store.base import Document, VectorStore


class Retriever:
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        top_k: int = 5,
        score_threshold: float | None = None,
    ):
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store
        self._top_k = top_k
        self._score_threshold = score_threshold if score_threshold is not None else settings.retrieval_score_threshold

    async def retrieve(
        self,
        query: str,
        user_id: str | None = None,
        config: RetrievalConfig | None = None,
    ) -> list[Document]:
        cfg = config or DEFAULT_CONFIG
        top_k = cfg.top_k
        score_threshold = cfg.score_threshold if cfg.score_threshold is not None else self._score_threshold

        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("rag.retrieve") as span:
            span.set_attribute("query_len", len(query))
            span.set_attribute("top_k", top_k)
            span.set_attribute("score_threshold", score_threshold)
            span.set_attribute("config_name", cfg.name)
            span.set_attribute("user_filter", bool(user_id))
            logger.debug(f"Retrieving context for: {query[:50]}... (config={cfg.name}, top_k={top_k})")

            query_digest = hashlib.sha256(query.encode("utf-8")).hexdigest()[:32]
            cache_key = f"retrieve:{query_digest}:user={user_id or 'none'}:cfg={cfg.name}"
            cached = await rag_cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit for query")
                span.set_attribute("cache_hit", True)
                RETRIEVAL_QUERIES.labels(config_name=cfg.name, cache_hit="true").inc()
                RETRIEVAL_LATENCY.observe(0)
                return [Document(**d) for d in cached]
            span.set_attribute("cache_hit", False)
            RETRIEVAL_QUERIES.labels(config_name=cfg.name, cache_hit="false").inc()

            start = time.perf_counter()

            with tracer.start_as_current_span("rag.embed_query") as embed_span:
                query_embedding = await self._embedding_provider.embed_query(query)
                embed_span.set_attribute("embedding_dim", len(query_embedding))

            with tracer.start_as_current_span("rag.similarity_search") as search_span:
                results = await self._vector_store.similarity_search(
                    query_embedding=query_embedding,
                    k=top_k,
                    score_threshold=score_threshold,
                    query_str=query,
                    user_id=user_id,
                )
                search_span.set_attribute("result_count", len(results))

            duration = time.perf_counter() - start
            RETRIEVAL_LATENCY.observe(duration)
            RETRIEVAL_RESULTS.observe(len(results))
            for doc in results:
                if doc.score is not None:
                    RETRIEVAL_SCORES.observe(doc.score)

            logger.debug(f"Retrieved {len(results)} relevant chunks (config={cfg.name}, threshold={score_threshold}, latency={duration:.3f}s)")
            span.set_attribute("result_count", len(results))
            span.set_attribute("latency_seconds", duration)

            doc_dicts = [d.__dict__ for d in results]
            await rag_cache.set(cache_key, doc_dicts, ttl=settings.cache_ttl_seconds)

            return results

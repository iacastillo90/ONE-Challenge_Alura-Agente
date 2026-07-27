import uuid

from loguru import logger
from opentelemetry import trace
from sqlalchemy import text

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.models import ChunkRecord
from app.rag.vector_store.base import CollectionStats, Document, VectorStore


class PgVectorStore(VectorStore):
    def __init__(self):
        logger.info("PgVectorStore initialized")

    async def add_texts(
        self,
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> list[str]:
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("pgvector.add_texts") as span:
            span.set_attribute("chunk_count", len(texts))
            ids = [str(uuid.uuid4()) for _ in texts]
            async with async_session_factory() as session:
                for i, text_content in enumerate(texts):
                    meta = metadatas[i]
                    chunk = ChunkRecord(
                        id=ids[i],
                        document_id=meta.get("document_id", ""),
                        user_id=meta.get("user_id", ""),
                        chunk_index=meta.get("chunk_index", i),
                        content=text_content,
                        metadata_=meta,
                        embedding=embeddings[i],
                    )
                    session.add(chunk)
                await session.commit()
            logger.debug(f"Added {len(texts)} chunks to pgvector")
            return ids

    async def similarity_search(
        self,
        query_embedding: list[float],
        k: int = 5,
        score_threshold: float = 0.0,
        query_str: str | None = None,
        user_id: str | None = None,
    ) -> list[Document]:
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("pgvector.similarity_search") as span:
            span.set_attribute("k", k)
            span.set_attribute("threshold", score_threshold)
            span.set_attribute("hybrid", settings.use_hybrid_search and bool(query_str))
            span.set_attribute("embedding_dim", len(query_embedding))
            span.set_attribute("user_filter", bool(user_id))

            emb_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

            if settings.use_hybrid_search and query_str:
                alpha = settings.hybrid_search_alpha
                sql = text("""
                    SELECT id, content, metadata, document_id, chunk_index,
                           :alpha * (1 - (embedding <=> :emb::vector))
                           + (1 - :alpha) * COALESCE(
                               ts_rank(to_tsvector('spanish', content),
                                       plainto_tsquery('spanish', :query)), 0
                           ) AS combined_score
                    FROM embeddings
                    WHERE (1 - (embedding <=> :emb::vector) >= :threshold
                       OR to_tsvector('spanish', content) @@ plainto_tsquery('spanish', :query))
                       AND (:user_id_param IS NULL OR user_id = :user_id_param)
                    ORDER BY combined_score DESC
                    LIMIT :k
                """)
            else:
                sql = text("""
                    SELECT id, content, metadata, document_id, chunk_index,
                           1 - (embedding <=> :emb::vector) AS combined_score
                    FROM embeddings
                    WHERE 1 - (embedding <=> :emb::vector) >= :threshold
                       AND (:user_id_param IS NULL OR user_id = :user_id_param)
                    ORDER BY combined_score DESC
                    LIMIT :k
                """)

            async with async_session_factory() as session:
                params: dict = {"k": k, "threshold": score_threshold, "emb": emb_str, "user_id_param": user_id}
                if settings.use_hybrid_search and query_str:
                    params["alpha"] = alpha
                    params["query"] = query_str
                rows = await session.execute(sql, params)
                results = rows.fetchall()

            span.set_attribute("result_count", len(results))
            return [
                Document(
                    id=str(r[0]),
                    content=r[1],
                    metadata={**(r[2] or {}), "document_id": r[3]},
                    score=float(r[4]) if r[4] is not None else None,
                )
                for r in results
            ]

    async def delete_document(self, document_id: str) -> None:
        async with async_session_factory() as session:
            await session.execute(
                text("DELETE FROM embeddings WHERE document_id = :did"),
                {"did": document_id},
            )
            await session.commit()
        logger.info(f"Deleted document chunks: {document_id}")

    async def get_collection_stats(self) -> CollectionStats:
        async with async_session_factory() as session:
            count = await session.execute(
                text("SELECT COALESCE(reltuples::bigint, 0) FROM pg_class WHERE relname = 'embeddings'")
            )
            cnt = count.scalar() or 0
        return CollectionStats(count=cnt, name="embeddings")

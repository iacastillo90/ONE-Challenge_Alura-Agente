from __future__ import annotations

import uuid

from loguru import logger

from app.core.config import settings
from app.rag.vector_store.base import CollectionStats, Document, VectorStore

COLLECTION_NAME = "documents"


class QdrantVectorStore(VectorStore):
    """Qdrant-backed vector store (production option).

    Requires the optional ``qdrant-client`` dependency. If it is not installed
    a clear, actionable error is raised instead of a bare ImportError.
    """

    def __init__(self, url: str = "", api_key: str = ""):
        try:
            from qdrant_client import AsyncQdrantClient
            from qdrant_client.http import models as qmodels
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "VECTOR_STORE_TYPE=qdrant requires the 'qdrant-client' package. "
                "Install it with: pip install qdrant-client"
            ) from exc

        self._qmodels = qmodels
        self._client = AsyncQdrantClient(url=url or settings.qdrant_url, api_key=api_key or settings.qdrant_api_key or None)
        self._dim = settings.embedding_dimension
        self._ready = False
        logger.info(f"QdrantVectorStore configured — url={url or settings.qdrant_url}")

    async def _ensure_collection(self) -> None:
        if self._ready:
            return
        qm = self._qmodels
        existing = await self._client.get_collections()
        names = {c.name for c in existing.collections}
        if COLLECTION_NAME not in names:
            await self._client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=qm.VectorParams(size=self._dim, distance=qm.Distance.COSINE),
            )
            # Index the user_id payload field for efficient per-user filtering.
            await self._client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="user_id",
                field_schema=qm.PayloadSchemaType.KEYWORD,
            )
            await self._client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="document_id",
                field_schema=qm.PayloadSchemaType.KEYWORD,
            )
        self._ready = True

    async def add_texts(
        self,
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> list[str]:
        await self._ensure_collection()
        qm = self._qmodels
        ids = [str(uuid.uuid4()) for _ in texts]
        points = [
            qm.PointStruct(
                id=ids[i],
                vector=embeddings[i],
                payload={**metadatas[i], "content": texts[i]},
            )
            for i in range(len(texts))
        ]
        await self._client.upsert(collection_name=COLLECTION_NAME, points=points)
        logger.debug(f"Added {len(texts)} chunks to qdrant")
        return ids

    async def similarity_search(
        self,
        query_embedding: list[float],
        k: int = 5,
        score_threshold: float = 0.0,
        query_str: str | None = None,
        user_id: str | None = None,
    ) -> list[Document]:
        await self._ensure_collection()
        qm = self._qmodels

        query_filter = None
        if user_id:
            query_filter = qm.Filter(
                must=[qm.FieldCondition(key="user_id", match=qm.MatchValue(value=user_id))]
            )

        results = await self._client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_embedding,
            limit=k,
            score_threshold=score_threshold or None,
            query_filter=query_filter,
            with_payload=True,
        )

        documents: list[Document] = []
        for point in results:
            payload = dict(point.payload or {})
            content = payload.pop("content", "")
            documents.append(
                Document(
                    id=str(point.id),
                    content=content,
                    metadata=payload,
                    score=float(point.score) if point.score is not None else None,
                )
            )
        return documents

    async def delete_document(self, document_id: str) -> None:
        await self._ensure_collection()
        qm = self._qmodels
        await self._client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=qm.FilterSelector(
                filter=qm.Filter(
                    must=[qm.FieldCondition(key="document_id", match=qm.MatchValue(value=document_id))]
                )
            ),
        )
        logger.info(f"Deleted document chunks from qdrant: {document_id}")

    async def get_collection_stats(self) -> CollectionStats:
        await self._ensure_collection()
        info = await self._client.count(collection_name=COLLECTION_NAME, exact=False)
        return CollectionStats(count=info.count, name=COLLECTION_NAME)

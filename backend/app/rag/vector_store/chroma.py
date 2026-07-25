import uuid

import chromadb
from loguru import logger

from app.rag.vector_store.base import CollectionStats, Document, VectorStore


class ChromaVectorStore(VectorStore):
    def __init__(self, persist_directory: str = "./chroma_data"):
        self._client = chromadb.PersistentClient(path=persist_directory)
        self._collection = self._client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"ChromaDB initialized — path={persist_directory}")

    async def add_texts(
        self,
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> list[str]:
        ids = [str(uuid.uuid4()) for _ in texts]

        self._collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
        logger.debug(f"Added {len(texts)} chunks to vector store")
        return ids

    async def similarity_search(
        self,
        query_embedding: list[float],
        k: int = 5,
        score_threshold: float = 0.0,
    ) -> list[Document]:
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
        )

        documents: list[Document] = []
        if not results["ids"]:
            return documents

        for i in range(len(results["ids"][0])):
            score = results["distances"][0][i] if results["distances"] else None
            score = 1 - score if score is not None else None

            if score is not None and score < score_threshold:
                continue

            documents.append(
                Document(
                    id=results["ids"][0][i],
                    content=results["documents"][0][i],
                    metadata=results["metadatas"][0][i],
                    score=score,
                )
            )

        return documents

    async def delete_document(self, document_id: str) -> None:
        self._collection.delete(where={"document_id": document_id})
        logger.info(f"Deleted document chunks: {document_id}")

    async def get_collection_stats(self) -> CollectionStats:
        count = self._collection.count()
        return CollectionStats(count=count, name="documents")

from __future__ import annotations

import math

import pytest

from app.rag.embeddings.local import LocalEmbeddingProvider
from app.rag.ingestion.loader import DocumentLoader
from app.rag.ingestion.processor import IngestionProcessor
from app.core.retrieval_config import RetrievalConfig
from app.rag.ingestion.splitter import RecursiveChunker
from app.rag.retrieval.retriever import Retriever
from app.rag.vector_store.base import CollectionStats, Document, VectorStore


class InMemoryVectorStore(VectorStore):
    """Dependency-free VectorStore for testing the RAG pipeline without a DB
    or external service. Implements cosine similarity in pure Python."""

    def __init__(self):
        self._items: list[dict] = []

    async def add_texts(self, texts, embeddings, metadatas):
        ids = []
        for i, text in enumerate(texts):
            item_id = f"chunk-{len(self._items)}"
            self._items.append(
                {"id": item_id, "content": text, "embedding": embeddings[i], "metadata": metadatas[i]}
            )
            ids.append(item_id)
        return ids

    @staticmethod
    def _cosine(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        return dot / (na * nb) if na and nb else 0.0

    async def similarity_search(self, query_embedding, k=5, score_threshold=0.0, query_str=None, user_id=None):
        scored = []
        for item in self._items:
            if user_id is not None and item["metadata"].get("user_id") not in (None, "", user_id):
                continue
            score = self._cosine(query_embedding, item["embedding"])
            if score >= score_threshold:
                scored.append(
                    Document(id=item["id"], content=item["content"], metadata=item["metadata"], score=score)
                )
        scored.sort(key=lambda d: d.score or 0.0, reverse=True)
        return scored[:k]

    async def delete_document(self, document_id: str) -> None:
        self._items = [i for i in self._items if i["metadata"].get("document_id") != document_id]

    async def get_collection_stats(self) -> CollectionStats:
        return CollectionStats(count=len(self._items), name="in-memory")


@pytest.fixture
def csv_sample(tmp_path):
    f = tmp_path / "test.csv"
    f.write_text("nombre,edad,ciudad\nAna,28,Bogotá\nCarlos,35,México DF\nLaura,22,Lima\n")
    return str(f)


@pytest.fixture
def pdf_sample(tmp_path):
    import fitz

    f = tmp_path / "test.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Este es un documento de prueba sobre inteligencia artificial.")
    doc.save(str(f))
    doc.close()
    return str(f)


@pytest.mark.asyncio
async def test_csv_loading(csv_sample):
    loader = DocumentLoader()
    text = await loader.load(csv_sample)
    assert "Ana" in text
    assert "Laura" in text
    assert len(text) > 0


@pytest.mark.asyncio
async def test_pdf_loading(pdf_sample):
    loader = DocumentLoader()
    text = await loader.load(pdf_sample)
    assert "inteligencia artificial" in text
    assert len(text) > 0


@pytest.mark.asyncio
async def test_chunking():
    splitter = RecursiveChunker(chunk_size=50, chunk_overlap=10)
    text = "Python es un lenguaje de programación.\n\nJavaScript es otro lenguaje.\n\nAmbos son muy populares."
    chunks = splitter.split_text(text, source="test")
    assert len(chunks) > 0
    assert all(c.metadata.get("source") == "test" for c in chunks)


@pytest.mark.asyncio
async def test_embeddings():
    provider = LocalEmbeddingProvider()
    emb = await provider.embed_texts(["hello world", "test sentence"])
    assert len(emb) == 2
    assert len(emb[0]) == 384


@pytest.mark.asyncio
async def test_vector_store():
    store = InMemoryVectorStore()
    embedder = LocalEmbeddingProvider()
    emb = await embedder.embed_texts(["test content"])
    ids = await store.add_texts(["test content"], emb, [{"doc": "test"}])
    assert len(ids) == 1

    results = await store.similarity_search(emb[0], k=1)
    assert len(results) == 1
    assert results[0].content == "test content"

    stats = await store.get_collection_stats()
    assert stats.count > 0


@pytest.mark.asyncio
async def test_full_rag_pipeline(csv_sample):
    embedder = LocalEmbeddingProvider()
    store = InMemoryVectorStore()
    processor = IngestionProcessor(
        loader=DocumentLoader(),
        splitter=RecursiveChunker(chunk_size=100, chunk_overlap=10),
        embedding_provider=embedder,
        vector_store=store,
    )

    count = await processor.process(csv_sample, document_id="test-pipeline", user_id="user-1")
    assert count > 0

    retriever = Retriever(embedder, store, top_k=3, score_threshold=0.0)
    # Use an explicit low-threshold config so retrieval is deterministic and not
    # subject to the global default score threshold.
    cfg = RetrievalConfig(name="test", top_k=3, score_threshold=0.0, use_hybrid_search=False)
    results = await retriever.retrieve("quién vive en Lima?", user_id="user-1", config=cfg)
    assert len(results) > 0

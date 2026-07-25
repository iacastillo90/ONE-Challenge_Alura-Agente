import asyncio

import pytest

from app.rag.embeddings.local import LocalEmbeddingProvider
from app.rag.ingestion.loader import DocumentLoader
from app.rag.ingestion.processor import IngestionProcessor
from app.rag.ingestion.splitter import SemanticChunker
from app.rag.retrieval.retriever import Retriever
from app.rag.vector_store.chroma import ChromaVectorStore


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
    splitter = SemanticChunker(chunk_size=50, chunk_overlap=10)
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
    store = ChromaVectorStore(persist_directory="/tmp/_test_chroma")
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
    store = ChromaVectorStore(persist_directory="/tmp/_test_pipeline")
    processor = IngestionProcessor(
        loader=DocumentLoader(),
        splitter=SemanticChunker(chunk_size=100, chunk_overlap=10),
        embedding_provider=embedder,
        vector_store=store,
    )

    count = await processor.process(csv_sample, document_id="test-pipeline")
    assert count > 0

    retriever = Retriever(embedder, store, top_k=3)
    results = await retriever.retrieve("quién vive en Lima?")
    assert len(results) > 0

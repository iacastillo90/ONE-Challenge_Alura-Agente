from fastapi import Depends
from loguru import logger

from app.core.config import settings as app_settings
from app.llm.providers.deepseek import DeepSeekProvider
from app.llm.providers.gemini import GeminiProvider
from app.llm.providers.groq import GroqProvider
from app.llm.providers.openai_compatible import OpenAICompatibleProvider
from app.llm.router import ProviderRouter
from app.memory.chat_history import ChatHistoryManager
from app.rag.embeddings.base import EmbeddingProvider as EmbeddingProviderABC
from app.rag.embeddings.local import LocalEmbeddingProvider
from app.rag.ingestion.loader import DocumentLoader
from app.rag.ingestion.processor import IngestionProcessor
from app.rag.ingestion.splitter import RecursiveChunker
from app.rag.retrieval.retriever import Retriever
from app.rag.vector_store.base import VectorStore as VectorStoreABC
from app.services.chat_service import ChatService
from app.services.document_service import DocumentService

_expensive_instances: dict[str, object] = {}


def _expensive(key: str, factory):
    if key not in _expensive_instances:
        _expensive_instances[key] = factory()
    return _expensive_instances[key]


def reset_dependency_overrides():
    _expensive_instances.clear()


def _build_providers() -> list:
    providers = []
    if app_settings.gemini_api_key:
        providers.append(GeminiProvider())
    if app_settings.groq_api_key:
        providers.append(GroqProvider())
    if app_settings.deepseek_api_key:
        providers.append(DeepSeekProvider())
    if app_settings.openai_compatible_api_key and app_settings.openai_compatible_base_url:
        providers.append(OpenAICompatibleProvider())
    if not providers:
        logger.warning("No LLM providers configured — falling back to all available")
        providers = [GeminiProvider(), GroqProvider(), DeepSeekProvider(), OpenAICompatibleProvider()]
    return providers


async def get_embedding_provider() -> EmbeddingProviderABC:
    def _build():
        if app_settings.embedding_provider == "api":
            from app.rag.embeddings.api import APIEmbeddingProvider
            return APIEmbeddingProvider()
        return LocalEmbeddingProvider(model_name=app_settings.embedding_model)
    return _expensive("embedding_provider", _build)


async def get_vector_store() -> VectorStoreABC:
    def _build():
        vs_type = app_settings.vector_store_type
        if vs_type == "pgvector":
            from app.rag.vector_store.pgvector import PgVectorStore
            return PgVectorStore()
        elif vs_type == "qdrant":
            from app.rag.vector_store.qdrant import QdrantVectorStore
            return QdrantVectorStore(url=app_settings.qdrant_url, api_key=app_settings.qdrant_api_key)
        from app.rag.vector_store.chroma import ChromaVectorStore
        return ChromaVectorStore(persist_directory="./chroma_data")
    return _expensive("vector_store", _build)


async def get_provider_router() -> ProviderRouter:
    def _build():
        return ProviderRouter(_build_providers())
    return _expensive("provider_router", _build)


async def get_chat_history() -> ChatHistoryManager:
    return ChatHistoryManager()


async def get_retriever(
    embedding: EmbeddingProviderABC = Depends(get_embedding_provider),
    store: VectorStoreABC = Depends(get_vector_store),
) -> Retriever:
    return Retriever(embedding_provider=embedding, vector_store=store)


async def get_processor(
    embedding: EmbeddingProviderABC = Depends(get_embedding_provider),
    store: VectorStoreABC = Depends(get_vector_store),
) -> IngestionProcessor:
    return IngestionProcessor(
        loader=DocumentLoader(),
        splitter=RecursiveChunker(),
        embedding_provider=embedding,
        vector_store=store,
    )


async def get_chat_service(
    router: ProviderRouter = Depends(get_provider_router),
    retriever: Retriever = Depends(get_retriever),
    history: ChatHistoryManager = Depends(get_chat_history),
) -> ChatService:
    return ChatService(router=router, retriever=retriever, history=history)


async def get_document_service(
    store: VectorStoreABC = Depends(get_vector_store),
) -> DocumentService:
    return DocumentService(vector_store=store)

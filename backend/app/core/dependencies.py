from fastapi import Depends
from loguru import logger

from app.core.config import Settings, settings as app_settings
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
from app.rag.ingestion.splitter import SemanticChunker
from app.rag.retrieval.retriever import Retriever
from app.rag.vector_store.base import VectorStore as VectorStoreABC
from app.rag.vector_store.chroma import ChromaVectorStore
from app.services.chat_service import ChatService
from app.services.document_service import DocumentService


async def get_settings() -> Settings:
    return app_settings


_embedding_provider: EmbeddingProviderABC | None = None
_vector_store: VectorStoreABC | None = None
_router: ProviderRouter | None = None
_history: ChatHistoryManager | None = None
_retriever: Retriever | None = None
_chat_service: ChatService | None = None
_document_service: DocumentService | None = None
_processor: IngestionProcessor | None = None


async def get_embedding_provider() -> EmbeddingProviderABC:
    global _embedding_provider
    if _embedding_provider is None:
        if app_settings.embedding_provider == "api":
            from app.rag.embeddings.api import APIEmbeddingProvider
            _embedding_provider = APIEmbeddingProvider()
        else:
            _embedding_provider = LocalEmbeddingProvider(model_name=app_settings.embedding_model)
        logger.info(f"Embedding provider initialized: {app_settings.embedding_provider}")
    return _embedding_provider


async def get_vector_store() -> VectorStoreABC:
    global _vector_store
    if _vector_store is None:
        if app_settings.vector_store_type == "qdrant":
            from app.rag.vector_store.qdrant import QdrantVectorStore
            _vector_store = QdrantVectorStore(
                url=app_settings.qdrant_url,
                api_key=app_settings.qdrant_api_key,
            )
        else:
            _vector_store = ChromaVectorStore(persist_directory="./chroma_data")
        logger.info(f"Vector store initialized: {app_settings.vector_store_type}")
    return _vector_store


async def get_provider_router() -> ProviderRouter:
    global _router
    if _router is None:
        providers = [
            GeminiProvider(),
            GroqProvider(),
            DeepSeekProvider(),
            OpenAICompatibleProvider(),
        ]
        _router = ProviderRouter(providers)
        logger.info("Provider router initialized with 4 providers")
    return _router


async def get_chat_history() -> ChatHistoryManager:
    global _history
    if _history is None:
        _history = ChatHistoryManager(db_path="./chat_history.db")
    return _history


async def get_retriever(
    embedding: EmbeddingProviderABC = Depends(get_embedding_provider),
    store: VectorStoreABC = Depends(get_vector_store),
) -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever(embedding_provider=embedding, vector_store=store)
    return _retriever


async def get_processor(
    embedding: EmbeddingProviderABC = Depends(get_embedding_provider),
    store: VectorStoreABC = Depends(get_vector_store),
) -> IngestionProcessor:
    global _processor
    if _processor is None:
        _processor = IngestionProcessor(
            loader=DocumentLoader(),
            splitter=SemanticChunker(),
            embedding_provider=embedding,
            vector_store=store,
        )
    return _processor


async def get_chat_service(
    router: ProviderRouter = Depends(get_provider_router),
    retriever: Retriever = Depends(get_retriever),
    history: ChatHistoryManager = Depends(get_chat_history),
) -> ChatService:
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService(router=router, retriever=retriever, history=history)
    return _chat_service


async def get_document_service(
    processor: IngestionProcessor = Depends(get_processor),
    store: VectorStoreABC = Depends(get_vector_store),
) -> DocumentService:
    global _document_service
    if _document_service is None:
        _document_service = DocumentService(processor=processor, vector_store=store)
    return _document_service

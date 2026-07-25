from pathlib import Path
from typing import AsyncGenerator

from loguru import logger

from app.core.config import settings
from app.llm.base import BaseProvider, Message, TokenEvent
from app.llm.router import ProviderRouter
from app.memory.chat_history import ChatHistoryManager
from app.rag.embeddings.base import EmbeddingProvider
from app.rag.retrieval.retriever import Retriever
from app.rag.vector_store.base import VectorStore


def _load_system_prompt() -> str:
    path = Path(settings.system_prompt_path)
    if path.exists():
        return path.read_text().strip()
    logger.warning(f"System prompt not found at {path}, using default")
    return "Eres un asistente de IA experto en análisis de documentos."


class ChatService:
    def __init__(
        self,
        router: ProviderRouter,
        retriever: Retriever,
        history: ChatHistoryManager,
    ):
        self._router = router
        self._retriever = retriever
        self._history = history
        self._system_prompt = _load_system_prompt()

    async def chat_stream(
        self,
        message: str,
        session_id: str,
    ) -> AsyncGenerator[TokenEvent, None]:
        logger.info(f"Chat request — session={session_id[:8]}...")

        sources = await self._retriever.retrieve(message)

        context_blocks = [
            f"[Fuente: {s.metadata.get('source', 'desconocida')}]\n{s.content}"
            for s in sources
        ]
        context = "\n\n".join(context_blocks) if context_blocks else ""

        history_messages = self._history.get_messages(session_id)

        llm_messages = [Message(role="system", content=self._system_prompt)]

        if context:
            llm_messages.append(
                Message(role="system", content=f"Contexto de documentos:\n\n{context}")
            )

        llm_messages.extend(history_messages)
        llm_messages.append(Message(role="user", content=message))

        self._history.add_message(session_id, Message(role="user", content=message))

        full_response = ""
        async for event in self._router.generate_stream(
            messages=llm_messages,
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
        ):
            if event.token:
                full_response += event.token
            yield event

        self._history.add_message(
            session_id, Message(role="assistant", content=full_response)
        )

        source_list = [
            {"document_name": s.metadata.get("source", ""), "chunk": s.content[:200], "score": s.score}
            for s in sources
        ]
        yield TokenEvent(token="", done=True, full_response=full_response, sources=source_list)

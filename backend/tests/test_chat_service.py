from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import RAGException
from app.core.retrieval_config import DEFAULT_CONFIG
from app.llm.base import Message, TokenEvent
from app.services.chat_service import ChatService


@pytest.fixture
def mock_router():
    router = MagicMock()
    router.get_active.return_value = None
    router.get_active_state.return_value = None

    async def mock_generate(messages, max_tokens=4096, temperature=0.7):
        yield TokenEvent(token="respuesta simulada")
        yield TokenEvent(token="", done=True, full_response="respuesta simulada")

    router.generate_stream = mock_generate
    return router


@pytest.fixture
def mock_retriever():
    retriever = AsyncMock()
    retriever.retrieve = AsyncMock(return_value=[])
    return retriever


@pytest.fixture
def mock_history():
    history = AsyncMock()
    history.get_messages = AsyncMock(return_value=[])
    return history


@pytest.fixture
def chat_service(mock_router, mock_retriever, mock_history):
    return ChatService(
        router=mock_router,
        retriever=mock_retriever,
        history=mock_history,
    )


@pytest.mark.asyncio
async def test_chat_stream_returns_token_events(chat_service, mock_retriever):
    with (
        patch("app.services.chat_service.experiment_service.resolve_config") as mock_resolve,
        patch("app.services.chat_service.token_quota") as mock_quota,
        patch("app.services.chat_service.token_counter") as mock_counter,
    ):
        mock_resolve.return_value = (DEFAULT_CONFIG, None)
        mock_quota.check_only = AsyncMock()
        mock_quota.check_and_consume = AsyncMock()
        mock_counter.count_messages.return_value = 20
        mock_counter.count.return_value = 5
        mock_retriever.retrieve.return_value = []

        tokens: list[TokenEvent] = []
        async for event in chat_service.chat_stream(
            message="hola",
            session_id="test-session",
            user_id="test-user",
        ):
            tokens.append(event)

        assert len(tokens) > 0
        assert all(isinstance(t, TokenEvent) for t in tokens)
        assert tokens[-1].done is True
        assert tokens[-1].full_response is not None


@pytest.mark.asyncio
async def test_chat_stream_includes_sources_when_retrieved(chat_service, mock_router, mock_retriever):
    from app.rag.vector_store.base import Document

    docs = [
        Document(id="1", content="contenido del documento", metadata={"source": "doc1.pdf"}, score=0.95),
        Document(id="2", content="otro documento", metadata={"source": "doc2.pdf"}, score=0.85),
    ]
    mock_retriever.retrieve.return_value = docs

    async def mock_generate(messages, max_tokens=4096, temperature=0.7):
        yield TokenEvent(token="basado en los documentos")
        yield TokenEvent(token="", done=True, full_response="basado en los documentos")

    mock_router.generate_stream = mock_generate

    with (
        patch("app.services.chat_service.experiment_service.resolve_config") as mock_resolve,
        patch("app.services.chat_service.token_quota") as mock_quota,
        patch("app.services.chat_service.token_counter") as mock_counter,
    ):
        mock_resolve.return_value = (DEFAULT_CONFIG, None)
        mock_quota.check_only = AsyncMock()
        mock_quota.check_and_consume = AsyncMock()
        mock_counter.count_messages.return_value = 30
        mock_counter.count.return_value = 5

        tokens = []
        async for event in chat_service.chat_stream(
            message="que dicen los documentos",
            session_id="test-session",
            user_id="test-user",
        ):
            tokens.append(event)

        done_event = tokens[-1]
        assert done_event.done is True
        assert done_event.sources is not None
        assert len(done_event.sources) == 2
        assert done_event.sources[0]["document_name"] == "doc1.pdf"
        assert done_event.sources[1]["document_name"] == "doc2.pdf"


@pytest.mark.asyncio
async def test_chat_stream_rejects_long_message(chat_service):
    with pytest.raises(RAGException, match="Message exceeds maximum length of 10000 characters"):
        async for _ in chat_service.chat_stream(
            message="x" * 10001,
            session_id="test-session",
            user_id="test-user",
        ):
            pass


@pytest.mark.asyncio
async def test_chat_stream_provider_unavailable(chat_service, mock_router):
    async def failing_generate(messages, max_tokens=4096, temperature=0.7):
        raise Exception("Provider timeout")
        yield  # pragma: no cover

    mock_router.generate_stream = failing_generate

    with (
        patch("app.services.chat_service.experiment_service.resolve_config") as mock_resolve,
        patch("app.services.chat_service.token_quota") as mock_quota,
        patch("app.services.chat_service.token_counter") as mock_counter,
    ):
        mock_resolve.return_value = (DEFAULT_CONFIG, None)
        mock_quota.check_only = AsyncMock()
        mock_quota.check_and_consume = AsyncMock()
        mock_counter.count_messages.return_value = 20
        mock_counter.count.return_value = 5

        with pytest.raises(Exception, match="Provider timeout"):
            async for _ in chat_service.chat_stream(
                message="hola",
                session_id="test-session",
                user_id="test-user",
            ):
                pass


@pytest.mark.asyncio
async def test_chat_stream_rag_retrieval_error(chat_service, mock_retriever):
    mock_retriever.retrieve.side_effect = RAGException("Error en recuperación de documentos")

    with (
        patch("app.services.chat_service.experiment_service.resolve_config") as mock_resolve,
    ):
        mock_resolve.return_value = (DEFAULT_CONFIG, None)

        with pytest.raises(RAGException, match="Error en recuperación de documentos"):
            async for _ in chat_service.chat_stream(
                message="consulta con error",
                session_id="test-session",
                user_id="test-user",
            ):
                pass


@pytest.mark.asyncio
async def test_chat_stream_applies_pii_filter(chat_service, mock_router, mock_retriever):
    async def mock_generate_with_pii(messages, max_tokens=4096, temperature=0.7):
        yield TokenEvent(token="mi email es test@example.com")
        yield TokenEvent(token="", done=True, full_response="mi email es test@example.com")

    mock_router.generate_stream = mock_generate_with_pii

    with (
        patch("app.services.chat_service.experiment_service.resolve_config") as mock_resolve,
        patch("app.services.chat_service.token_quota") as mock_quota,
        patch("app.services.chat_service.token_counter") as mock_counter,
    ):
        mock_resolve.return_value = (DEFAULT_CONFIG, None)
        mock_quota.check_only = AsyncMock()
        mock_quota.check_and_consume = AsyncMock()
        mock_counter.count_messages.return_value = 20
        mock_counter.count.return_value = 5
        mock_retriever.retrieve.return_value = []

        tokens = []
        async for event in chat_service.chat_stream(
            message="cual es tu email",
            session_id="test-session",
            user_id="test-user",
        ):
            tokens.append(event)

        done_event = tokens[-1]
        assert done_event.done is True
        assert done_event.full_response is not None
        assert "[EMAIL_REDACTED]" in done_event.full_response


@pytest.mark.asyncio
async def test_chat_stream_adds_messages_to_history(chat_service, mock_history):
    with (
        patch("app.services.chat_service.experiment_service.resolve_config") as mock_resolve,
        patch("app.services.chat_service.token_quota") as mock_quota,
        patch("app.services.chat_service.token_counter") as mock_counter,
    ):
        mock_resolve.return_value = (DEFAULT_CONFIG, None)
        mock_quota.check_only = AsyncMock()
        mock_quota.check_and_consume = AsyncMock()
        mock_counter.count_messages.return_value = 20
        mock_counter.count.return_value = 5

        async for _ in chat_service.chat_stream(
            message="hola mundo",
            session_id="session-123",
            user_id="user-456",
        ):
            pass

        assert mock_history.add_message.await_count == 2
        user_call = mock_history.add_message.await_args_list[0]
        assert user_call.args[2].role == "user"
        assert user_call.args[2].content == "hola mundo"
        assistant_call = mock_history.add_message.await_args_list[1]
        assert assistant_call.args[2].role == "assistant"


@pytest.mark.asyncio
async def test_chat_stream_uses_history_context(chat_service, mock_history):
    mock_history.get_messages.return_value = [
        Message(role="user", content="pregunta anterior"),
        Message(role="assistant", content="respuesta anterior"),
    ]

    with (
        patch("app.services.chat_service.experiment_service.resolve_config") as mock_resolve,
        patch("app.services.chat_service.token_quota") as mock_quota,
        patch("app.services.chat_service.token_counter") as mock_counter,
    ):
        mock_resolve.return_value = (DEFAULT_CONFIG, None)
        mock_quota.check_only = AsyncMock()
        mock_quota.check_and_consume = AsyncMock()
        mock_counter.count_messages.return_value = 20
        mock_counter.count.return_value = 5

        async for _ in chat_service.chat_stream(
            message="siguiente pregunta",
            session_id="session-123",
            user_id="user-456",
        ):
            pass

        mock_history.get_messages.assert_awaited_once_with("session-123", "user-456")


@pytest.mark.asyncio
async def test_chat_stream_token_usage_in_done_event(chat_service):
    with (
        patch("app.services.chat_service.experiment_service.resolve_config") as mock_resolve,
        patch("app.services.chat_service.token_quota") as mock_quota,
        patch("app.services.chat_service.token_counter") as mock_counter,
    ):
        mock_resolve.return_value = (DEFAULT_CONFIG, None)
        mock_quota.check_only = AsyncMock()
        mock_quota.check_and_consume = AsyncMock()
        mock_counter.count_messages.return_value = 25
        mock_counter.count.return_value = 10

        tokens = []
        async for event in chat_service.chat_stream(
            message="test de tokens",
            session_id="test-session",
            user_id="test-user",
        ):
            tokens.append(event)

        done_event = tokens[-1]
        assert done_event.input_tokens > 0
        assert done_event.output_tokens > 0

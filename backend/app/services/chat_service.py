from pathlib import Path
from typing import AsyncGenerator

from loguru import logger
from opentelemetry import trace

from app.core.config import settings
from app.core.exceptions import RAGException
from app.core.otel import end_span, start_span
from app.core.security import (assert_safe_content, moderate_output, sanitize_pii, StreamingSanitizer)
from app.core.token_quota import token_quota
from app.core.tokenizer import token_counter
from app.llm.base import Message, TokenEvent
from app.llm.router import ProviderRouter
from app.memory.chat_history import ChatHistoryManager
from app.rag.retrieval.retriever import Retriever
from app.services import experiment_service
from app.services.query_rewriter import QueryRewriter

DELIMITER_START = "<contexto_documentos>"
DELIMITER_END = "</contexto_documentos>"


def _load_system_prompt() -> str:
    path = Path(settings.system_prompt_path)
    if path.exists():
        return path.read_text().strip()
    logger.warning(f"System prompt not found at {path}, using default")
    return "Eres un asistente de IA experto en análisis de documentos."


def _estimate_context_tokens(text: str) -> int:
    return token_counter.count(text)


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
        self._query_rewriter = QueryRewriter(llm_generate=self._router.generate_stream)

    async def chat_stream(
        self,
        message: str,
        session_id: str,
        user_id: str,
    ) -> AsyncGenerator[TokenEvent, None]:
        chat_span = start_span("chat.stream", {
            "session_id": session_id[:8],
            "message_len": len(message),
            "user_id": user_id[:8],
        })
        logger.info(f"Chat request — session={session_id[:8]}... user={user_id[:8]}...")

        try:
            assert_safe_content(message, context="user message")

            if len(message) > 10000:
                raise RAGException("Message exceeds maximum length of 10000 characters")

            retrieval_config, experiment_id = await experiment_service.resolve_config(user_id)
            logger.debug(f"Experiment for user {user_id[:8]}...: config={retrieval_config.name}, id={experiment_id}")

            history_messages = await self._history.get_messages(session_id, user_id)

            with trace.get_tracer(__name__).start_as_current_span("chat.rewrite_query"):
                rewritten = await self._query_rewriter.rewrite(
                    message,
                    history=[m.__dict__ for m in history_messages],
                )
            logger.debug(f"Original: {message[:50]}... Rewritten: {rewritten[:50]}...")

            sources = await self._retriever.retrieve(rewritten, user_id=user_id, config=retrieval_config)

            for s in sources:
                assert_safe_content(s.content, context=f"retrieved document {s.metadata.get('source', 'unknown')}")

            llm_messages = [Message(role="system", content=self._system_prompt)]

            if sources:
                max_context_chars = 40000
                context_lines = []
                context_chars = 0
                for s in sources:
                    block = f"[Fuente: {s.metadata.get('source', 'desconocida')}]\n{s.content}"
                    if context_chars + len(block) > max_context_chars:
                        remaining = max_context_chars - context_chars
                        if remaining > 100:
                            context_lines.append(block[:remaining] + "\n[...truncado]")
                        break
                    context_lines.append(block)
                    context_chars += len(block)
                context = "\n\n".join(context_lines)
                llm_messages.append(
                    Message(
                        role="system",
                        content=f"Contexto de documentos:\n{DELIMITER_START}\n{context}\n{DELIMITER_END}",
                    )
                )

            await self._history.add_message(session_id, user_id, Message(role="user", content=message))

            llm_messages.extend(history_messages)
            llm_messages.append(Message(role="user", content=rewritten))

            llm_dicts = [{"role": m.role, "content": m.content} for m in llm_messages]
            input_tokens = token_counter.count_messages(llm_dicts)
            estimated_output = min(settings.max_tokens, 2048)
            await token_quota.check_only(user_id, input_tokens, estimated_output)
            active_provider = self._router.get_active_state()
            context_window = active_provider.context_window if active_provider else 8192
            max_allowed = context_window - settings.max_tokens
            logger.debug(f"Prompt tokens: {input_tokens} (context window: ~{context_window})")

            if input_tokens > max_allowed:
                logger.warning(f"Token limit approaching: {input_tokens}/{max_allowed}")
                protected = 2 if context else 1
                truncated = token_counter.truncate_messages(llm_dicts, max_allowed, protected_count=protected)
                llm_messages = [Message(**m) for m in truncated]
                logger.info(f"Truncated to {len(llm_messages)} messages ({token_counter.count_messages(llm_dicts)} tokens)")

            full_response = ""
            sanitizer = StreamingSanitizer(buffer_size=100)
            llm_span = start_span("llm.generate", {
                "max_tokens": settings.max_tokens,
                "temperature": settings.temperature,
                "provider": self._router.get_active() or "auto",
            })
            try:
                async for event in self._router.generate_stream(
                    messages=llm_messages,
                    max_tokens=settings.max_tokens,
                    temperature=settings.temperature,
                ):
                    if event.token:
                        full_response += event.token
                        safe_token = sanitizer.process_token(event.token)
                        if safe_token:
                            event.token = safe_token
                            yield event
                    else:
                        yield event
            except Exception as e:
                end_span(llm_span, e)
                raise
            end_span(llm_span)

            safe_response = moderate_output(sanitize_pii(full_response))
            remaining = sanitizer.flush()
            if remaining:
                safe_response = moderate_output(sanitize_pii(remaining + safe_response))

            await self._history.add_message(
                session_id, user_id, Message(role="assistant", content=safe_response)
            )

            source_list = [
                {
                    "document_name": s.metadata.get("source", ""),
                    "score": round(s.score, 4),
                }
                for s in sources
            ]
            chat_span.set_attribute("source_count", len(source_list))
            chat_span.set_attribute("response_len", len(safe_response))
            input_tokens = token_counter.count_messages(llm_dicts)
            output_tokens = token_counter.count(safe_response) if safe_response else 0
            logger.info(f"Token usage — session={session_id[:8]} input={input_tokens} output={output_tokens}")
            await token_quota.check_and_consume(user_id, input_tokens, output_tokens)
            yield TokenEvent(
                token="", done=True, full_response=safe_response,
                sources=source_list, experiment_id=experiment_id,
                input_tokens=input_tokens, output_tokens=output_tokens,
            )
        except Exception as e:
            end_span(chat_span, e)
            raise
        finally:
            end_span(chat_span)

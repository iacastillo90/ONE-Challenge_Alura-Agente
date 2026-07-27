import json
import secrets

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.core.auth import verify_jwt
from app.core.dependencies import get_chat_service
from app.core.exceptions import ProviderUnavailableError, RAGException
from app.services.chat_service import ChatService

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    session_id: str | None = None


@router.post("")
async def chat(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
    user_id: str = Depends(verify_jwt),
):
    session_id = request.session_id or secrets.token_hex(16)

    async def event_generator():
        try:
            async for event in chat_service.chat_stream(
                message=request.message,
                session_id=session_id,
                user_id=user_id,
            ):
                if event.done:
                    yield {
                        "event": "done",
                        "data": json.dumps({
                            "full_response": event.full_response or "",
                            "sources": event.sources or [],
                            "session_id": session_id,
                        }),
                    }
                else:
                    yield {
                        "event": "token",
                        "data": json.dumps({"token": event.token}),
                    }
        except ProviderUnavailableError:
            yield {
                "event": "error",
                "data": json.dumps({"code": "PROVIDER_UNAVAILABLE", "message": "No hay proveedor LLM disponible. Verifica tus API keys."}),
            }
        except RAGException:
            yield {
                "event": "error",
                "data": json.dumps({"code": "RAG_ERROR", "message": "Error al recuperar contexto de documentos."}),
            }
        except Exception:
            yield {
                "event": "error",
                "data": json.dumps({"code": "INTERNAL_ERROR", "message": "Error interno del servidor"}),
            }

    return EventSourceResponse(event_generator(), ping=15)

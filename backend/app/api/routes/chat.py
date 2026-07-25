import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.core.dependencies import get_chat_service
from app.core.exceptions import ProviderUnavailableError, RAGException
from app.services.chat_service import ChatService

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


@router.post("")
async def chat(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
):
    async def event_generator():
        try:
            async for event in chat_service.chat_stream(
                message=request.message,
                session_id=request.session_id,
            ):
                if event.done:
                    yield {
                        "event": "done",
                        "data": json.dumps({
                            "full_response": event.full_response or "",
                            "sources": event.sources or [],
                        }),
                    }
                else:
                    yield {
                        "event": "token",
                        "data": json.dumps({"token": event.token}),
                    }
        except ProviderUnavailableError as e:
            yield {
                "event": "error",
                "data": json.dumps({"code": "PROVIDER_UNAVAILABLE", "message": str(e)}),
            }
        except RAGException as e:
            yield {
                "event": "error",
                "data": json.dumps({"code": "RAG_ERROR", "message": str(e)}),
            }
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"code": "INTERNAL_ERROR", "message": "Error interno del servidor"}),
            }

    return EventSourceResponse(event_generator())

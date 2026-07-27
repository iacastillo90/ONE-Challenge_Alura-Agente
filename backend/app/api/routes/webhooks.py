"""n8n / WhatsApp integration webhooks.

These endpoints let n8n bridge external channels (primarily WhatsApp) to the
same RAG chat + document pipeline the web UI uses. They are authenticated with
a shared secret (``X-Webhook-Secret``) rather than a user JWT, because the
caller is n8n, not an end user. Each phone number is mapped to an isolated
backend user so its documents and chat history stay private.

Flow (WhatsApp):
    WhatsApp -> n8n trigger -> POST /webhooks/chat (or /webhooks/documents)
             -> backend runs RAG -> reply -> n8n -> WhatsApp
"""

from __future__ import annotations

import base64
import hmac

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from loguru import logger
from pydantic import BaseModel, Field

from app.core.auth import get_or_create_channel_user, verify_jwt
from app.core.config import settings
from app.core.dependencies import get_chat_service, get_document_service
from app.services.chat_service import ChatService
from app.services.document_service import DocumentService

router = APIRouter()

MAX_UPLOAD_BYTES = settings.max_upload_size_mb * 1024 * 1024


async def verify_webhook_secret(x_webhook_secret: str | None = Header(default=None)) -> bool:
    """Authenticate an inbound webhook call from n8n via a shared secret."""
    if not settings.n8n_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhooks are not configured")
    if not x_webhook_secret or not hmac.compare_digest(x_webhook_secret, settings.n8n_webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
    return True


def _normalize_phone(phone: str) -> str:
    cleaned = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
    return cleaned.lstrip("+")


class WebhookChatRequest(BaseModel):
    phone: str = Field(..., min_length=5, max_length=32, description="Sender phone (E.164 or digits)")
    message: str = Field(..., min_length=1, max_length=10000)
    session_id: str | None = None


class WebhookChatResponse(BaseModel):
    reply: str
    sources: list[dict]
    session_id: str
    user_id: str


class WebhookDocumentRequest(BaseModel):
    phone: str = Field(..., min_length=5, max_length=32)
    filename: str = Field(..., min_length=1, max_length=512)
    content_base64: str = Field(..., description="Base64-encoded file bytes")


class WebhookDocumentResponse(BaseModel):
    id: str
    filename: str
    status: str


class WhatsAppSendRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4096)
    to: str | None = Field(default=None, description="Destination number; defaults to platform number")


class WhatsAppSendResponse(BaseModel):
    status: str
    to: str


@router.post("/chat", response_model=WebhookChatResponse)
async def webhook_chat(
    request: WebhookChatRequest,
    _: bool = Depends(verify_webhook_secret),
    chat_service: ChatService = Depends(get_chat_service),
):
    """Inbound chat from an external channel (n8n/WhatsApp). Non-streaming:
    returns the full reply so n8n can forward it in one message."""
    phone = _normalize_phone(request.phone)
    user_id = await get_or_create_channel_user("wa", phone)
    session_id = request.session_id or f"wa:{phone}"

    reply = ""
    sources: list[dict] = []
    try:
        async for event in chat_service.chat_stream(
            message=request.message,
            session_id=session_id,
            user_id=user_id,
        ):
            if event.done:
                reply = event.full_response or ""
                sources = event.sources or []
    except Exception as exc:  # noqa: BLE001 - surface a safe message to n8n
        logger.error(f"Webhook chat failed for wa:{phone[:4]}...: {exc}")
        raise HTTPException(status_code=502, detail="No se pudo generar una respuesta en este momento")

    return WebhookChatResponse(reply=reply, sources=sources, session_id=session_id, user_id=user_id)


@router.post("/documents", response_model=WebhookDocumentResponse)
async def webhook_document(
    request: WebhookDocumentRequest,
    _: bool = Depends(verify_webhook_secret),
    doc_service: DocumentService = Depends(get_document_service),
):
    """Inbound document from WhatsApp (base64). n8n downloads the media from the
    WhatsApp provider and forwards the bytes here for ingestion."""
    phone = _normalize_phone(request.phone)
    user_id = await get_or_create_channel_user("wa", phone)

    try:
        content = base64.b64decode(request.content_base64, validate=True)
    except Exception:
        raise HTTPException(status_code=422, detail="content_base64 inválido")

    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"Archivo demasiado grande (máx {settings.max_upload_size_mb}MB)")

    ext = request.filename.rsplit(".", 1)[-1].lower() if "." in request.filename else ""
    if ext:
        ext = f".{ext}"
    if ext not in doc_service.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=422, detail=f"Extensión no soportada: {ext}")

    result = await doc_service.upload(filename=request.filename, content=content, user_id=user_id)
    return WebhookDocumentResponse(id=result["id"], filename=result["filename"], status=result["status"])


async def send_whatsapp_via_n8n(to: str, message: str) -> None:
    """POST an outbound WhatsApp message to the configured n8n webhook.

    n8n owns the WhatsApp provider credentials; the backend only tells it what
    to send and to whom, authenticated with the shared secret.
    """
    if not settings.n8n_outbound_url:
        raise HTTPException(status_code=503, detail="Outbound WhatsApp (N8N_OUTBOUND_URL) is not configured")
    headers = {"Content-Type": "application/json"}
    if settings.n8n_webhook_secret:
        headers["X-Webhook-Secret"] = settings.n8n_webhook_secret
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            settings.n8n_outbound_url,
            json={"to": to, "message": message},
            headers=headers,
        )
        resp.raise_for_status()


@router.post("/whatsapp/send", response_model=WhatsAppSendResponse)
async def whatsapp_send(
    request: WhatsAppSendRequest,
    http_request: Request,
    user_id: str = Depends(verify_jwt),
):
    """Platform-authenticated endpoint: a logged-in user sends a WhatsApp message
    to a specified number (or the platform default) through n8n."""
    if not settings.whatsapp_enabled:
        raise HTTPException(status_code=403, detail="WhatsApp integration is disabled")

    to = request.to or settings.whatsapp_default_number
    if not to:
        raise HTTPException(status_code=422, detail="No destination number provided and no default configured")

    try:
        await send_whatsapp_via_n8n(_normalize_phone(to), request.message)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Outbound WhatsApp send failed: {exc}")
        raise HTTPException(status_code=502, detail="No se pudo enviar el mensaje de WhatsApp")

    from app.core.auth import audit_log

    await audit_log(
        user_id, "whatsapp.send", resource="whatsapp", details={"to": _normalize_phone(to)[:6] + "..."},
        ip_address=http_request.client.host if http_request.client else None,
    )
    return WhatsAppSendResponse(status="sent", to=to)

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from app.core.auth import verify_jwt
from app.core.database import async_session_factory
from app.core.dependencies import get_chat_history
from app.core.models import ChatSessionRecord
from app.memory.chat_history import ChatHistoryManager

router = APIRouter()


class SessionSummary(BaseModel):
    session_id: str
    message_count: int
    created_at: str
    updated_at: str


class SessionMessages(BaseModel):
    session_id: str
    messages: list[dict]


class PaginatedSessions(BaseModel):
    sessions: list[SessionSummary]
    total: int
    limit: int
    offset: int


@router.get("", response_model=PaginatedSessions)
async def list_sessions(
    user_id: str = Depends(verify_jwt),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    async with async_session_factory() as session:
        count_q = select(func.count(ChatSessionRecord.session_id)).where(
            ChatSessionRecord.user_id == user_id
        )
        total = (await session.execute(count_q)).scalar() or 0

        rows = await session.execute(
            select(ChatSessionRecord)
            .where(ChatSessionRecord.user_id == user_id)
            .order_by(ChatSessionRecord.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        records = rows.scalars().all()
        return PaginatedSessions(
            sessions=[
                SessionSummary(
                    session_id=r.session_id,
                    message_count=len(json.loads(r.messages)) if r.messages else 0,
                    created_at=r.created_at.isoformat(),
                    updated_at=r.updated_at.isoformat(),
                )
                for r in records
            ],
            total=total,
            limit=limit,
            offset=offset,
        )


@router.get("/{session_id}", response_model=SessionMessages)
async def get_session(
    session_id: str,
    user_id: str = Depends(verify_jwt),
    history: ChatHistoryManager = Depends(get_chat_history),
):
    messages = await history.get_messages(session_id, user_id, max_history=1000)
    if not messages:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionMessages(
        session_id=session_id,
        messages=[m.__dict__ for m in messages],
    )


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    user_id: str = Depends(verify_jwt),
    history: ChatHistoryManager = Depends(get_chat_history),
):
    await history.clear_session(session_id, user_id)
    return {"status": "deleted", "session_id": session_id}

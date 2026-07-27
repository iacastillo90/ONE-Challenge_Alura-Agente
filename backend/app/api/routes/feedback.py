import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.auth import verify_jwt
from app.core.database import async_session_factory
from app.core.models import FeedbackRecord

router = APIRouter()


class FeedbackRequest(BaseModel):
    session_id: str
    message_index: int = 0
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = None
    experiment_id: str | None = None


class FeedbackResponse(BaseModel):
    id: str
    status: str


@router.post("", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    user_id: str = Depends(verify_jwt),
):
    record = FeedbackRecord(
        id=str(uuid.uuid4()),
        user_id=user_id,
        session_id=request.session_id,
        message_index=request.message_index,
        rating=request.rating,
        comment=request.comment,
        experiment_id=request.experiment_id,
        created_at=datetime.now(timezone.utc),
    )
    async with async_session_factory() as session:
        session.add(record)
        await session.commit()
    return FeedbackResponse(id=record.id, status="recorded")

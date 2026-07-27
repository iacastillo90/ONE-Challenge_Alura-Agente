import json
from datetime import UTC, datetime

from loguru import logger
from sqlalchemy import and_, select

from app.core.cache import dist_lock
from app.core.database import async_session_factory
from app.core.models import ChatSessionRecord
from app.llm.base import Message


class ChatHistoryManager:

    async def get_messages(self, session_id: str, user_id: str, max_history: int = 50) -> list[Message]:
        async with async_session_factory() as session:
            row = await session.execute(
                select(ChatSessionRecord).where(
                    and_(
                        ChatSessionRecord.session_id == session_id,
                        ChatSessionRecord.user_id == user_id,
                    )
                )
            )
            record = row.scalar_one_or_none()

        if not record:
            return []

        messages = json.loads(record.messages)
        return [Message(**m) for m in messages[-max_history:]]

    async def add_message(self, session_id: str, user_id: str, message: Message, max_history: int = 50):
        if len(message.content) > 50000:
            message.content = message.content[:50000]
        lock = await dist_lock.run_with_lock(f"chat_session:{session_id}", timeout=10)
        async with lock:
            async with async_session_factory() as db_session:
                existing = await db_session.execute(
                    select(ChatSessionRecord).where(
                        and_(
                            ChatSessionRecord.session_id == session_id,
                            ChatSessionRecord.user_id == user_id,
                        )
                    )
                )
                record = existing.scalar_one_or_none()

                if record:
                    messages = json.loads(record.messages)
                else:
                    messages = []

                messages.append(message.__dict__)

                if len(messages) > max_history:
                    messages = messages[-max_history:]

                now = datetime.now(UTC)
                if record:
                    record.messages = json.dumps(messages)
                    record.max_history = max_history
                    record.updated_at = now
                else:
                    record = ChatSessionRecord(
                        session_id=session_id,
                        user_id=user_id,
                        messages=json.dumps(messages),
                        max_history=max_history,
                        created_at=now,
                        updated_at=now,
                    )
                    db_session.add(record)

                await db_session.commit()

    async def clear_session(self, session_id: str, user_id: str):
        async with async_session_factory() as session:
            existing = await session.execute(
                select(ChatSessionRecord).where(
                    and_(
                        ChatSessionRecord.session_id == session_id,
                        ChatSessionRecord.user_id == user_id,
                    )
                )
            )
            record = existing.scalar_one_or_none()
            if record is None:
                logger.warning(f"Clear session failed: session {session_id} not found for user {user_id[:8]}...")
                return
            await session.delete(record)
            await session.commit()
        logger.info(f"Cleared session: {session_id}")

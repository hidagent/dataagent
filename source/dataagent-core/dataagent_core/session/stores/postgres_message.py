"""PostgreSQL message store implementation using SQLAlchemy."""

import logging
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker

from dataagent_core.session.message_store import Message, MessageStore
from dataagent_core.session.models import MessageModel

logger = logging.getLogger(__name__)


class PostgresMessageStore(MessageStore):
    """PostgreSQL message store implementation.
    
    Uses SQLAlchemy async engine with connection pooling.
    Shares the engine with PostgresSessionStore for efficiency.
    
    Args:
        engine: SQLAlchemy async engine (shared with session store).
    """
    
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine
        self._session_factory = sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    
    def _model_to_message(self, model: MessageModel) -> Message:
        """Convert SQLAlchemy model to Message dataclass."""
        return Message(
            message_id=model.message_id,
            session_id=model.session_id,
            role=model.role,
            content=model.content,
            created_at=model.created_at,
            metadata=model.metadata_ or {},
        )
    
    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Save a message."""
        message = Message.create(
            session_id=session_id,
            role=role,
            content=content,
            metadata=metadata,
        )
        
        model = MessageModel(
            message_id=message.message_id,
            session_id=message.session_id,
            role=message.role,
            content=message.content,
            created_at=message.created_at,
            metadata_=message.metadata,
        )
        
        async with self._session_factory() as db:
            db.add(model)
            await db.commit()
            logger.debug(f"Saved message: {message.message_id}")
        
        return message.message_id
    
    async def get_messages(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Message]:
        """Get messages for a session."""
        async with self._session_factory() as db:
            result = await db.execute(
                select(MessageModel)
                .where(MessageModel.session_id == session_id)
                .order_by(MessageModel.created_at.asc())
                .limit(limit)
                .offset(offset)
            )
            models = result.scalars().all()
            return [self._model_to_message(m) for m in models]
    
    async def delete_messages(self, session_id: str) -> int:
        """Delete all messages for a session."""
        async with self._session_factory() as db:
            result = await db.execute(
                delete(MessageModel).where(MessageModel.session_id == session_id)
            )
            await db.commit()
            count = result.rowcount
            
            if count > 0:
                logger.debug(f"Deleted {count} messages for session: {session_id}")
            
            return count
    
    async def count_messages(self, session_id: str) -> int:
        """Count messages for a session."""
        async with self._session_factory() as db:
            result = await db.execute(
                select(func.count(MessageModel.message_id))
                .where(MessageModel.session_id == session_id)
            )
            return result.scalar() or 0

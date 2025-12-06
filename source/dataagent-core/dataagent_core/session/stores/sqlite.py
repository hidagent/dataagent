"""SQLite session store implementation using SQLAlchemy."""

import logging
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from dataagent_core.session.models import Base, SessionModel
from dataagent_core.session.state import Session
from dataagent_core.session.store import SessionStore

logger = logging.getLogger(__name__)


class SQLiteSessionStore(SessionStore):
    """SQLite session store implementation.
    
    Uses SQLAlchemy async engine with aiosqlite for async SQLite access.
    Ideal for development and single-instance deployments.
    
    Args:
        db_path: Path to SQLite database file. Defaults to ~/.dataagent/dataagent.db
    """
    
    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            db_path = Path.home() / ".dataagent" / "dataagent.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        url = f"sqlite+aiosqlite:///{self.db_path}"
        self._engine = create_async_engine(url, echo=False)
        self._session_factory = sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    
    async def init_tables(self) -> None:
        """Initialize database tables."""
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info(f"SQLite database initialized: {self.db_path}")
    
    async def close(self) -> None:
        """Close the database engine."""
        await self._engine.dispose()
        logger.info("SQLite connections closed")

    def _model_to_session(self, model: SessionModel) -> Session:
        """Convert SQLAlchemy model to Session dataclass."""
        return Session(
            session_id=model.session_id,
            user_id=model.user_id,
            assistant_id=model.assistant_id,
            created_at=model.created_at,
            last_active=model.last_active,
            state=model.state or {},
            metadata=model.metadata_ or {},
        )
    
    def _session_to_model(self, session: Session) -> SessionModel:
        """Convert Session dataclass to SQLAlchemy model."""
        return SessionModel(
            session_id=session.session_id,
            user_id=session.user_id,
            assistant_id=session.assistant_id,
            created_at=session.created_at,
            last_active=session.last_active,
            state=session.state,
            metadata_=session.metadata,
        )
    
    async def create(self, user_id: str, assistant_id: str) -> Session:
        """Create a new session."""
        session = Session.create(user_id=user_id, assistant_id=assistant_id)
        model = self._session_to_model(session)
        
        async with self._session_factory() as db:
            db.add(model)
            await db.commit()
            logger.debug(f"Created session: {session.session_id}")
        
        return session
    
    async def get(self, session_id: str) -> Session | None:
        """Get a session by ID."""
        async with self._session_factory() as db:
            result = await db.execute(
                select(SessionModel).where(SessionModel.session_id == session_id)
            )
            model = result.scalar_one_or_none()
            
            if model is None:
                return None
            
            return self._model_to_session(model)
    
    async def update(self, session: Session) -> None:
        """Update an existing session."""
        async with self._session_factory() as db:
            result = await db.execute(
                select(SessionModel).where(SessionModel.session_id == session.session_id)
            )
            model = result.scalar_one_or_none()
            
            if model is not None:
                model.user_id = session.user_id
                model.assistant_id = session.assistant_id
                model.last_active = session.last_active
                model.state = session.state
                model.metadata_ = session.metadata
                await db.commit()
                logger.debug(f"Updated session: {session.session_id}")
    
    async def delete(self, session_id: str) -> None:
        """Delete a session."""
        async with self._session_factory() as db:
            await db.execute(
                delete(SessionModel).where(SessionModel.session_id == session_id)
            )
            await db.commit()
            logger.debug(f"Deleted session: {session_id}")
    
    async def list_by_user(self, user_id: str) -> list[Session]:
        """List all sessions for a user."""
        async with self._session_factory() as db:
            result = await db.execute(
                select(SessionModel)
                .where(SessionModel.user_id == user_id)
                .order_by(SessionModel.last_active.desc())
            )
            models = result.scalars().all()
            return [self._model_to_session(m) for m in models]
    
    async def list_by_assistant(self, assistant_id: str) -> list[Session]:
        """List all sessions for an assistant."""
        async with self._session_factory() as db:
            result = await db.execute(
                select(SessionModel)
                .where(SessionModel.assistant_id == assistant_id)
                .order_by(SessionModel.last_active.desc())
            )
            models = result.scalars().all()
            return [self._model_to_session(m) for m in models]
    
    async def cleanup_expired(self, timeout_seconds: float) -> int:
        """Clean up expired sessions."""
        cutoff = datetime.now() - timedelta(seconds=timeout_seconds)
        
        async with self._session_factory() as db:
            result = await db.execute(
                delete(SessionModel).where(SessionModel.last_active < cutoff)
            )
            await db.commit()
            count = result.rowcount
            
            if count > 0:
                logger.info(f"Cleaned up {count} expired sessions")
            
            return count

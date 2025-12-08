"""Database factory for creating database connections.

Supports both SQLite (development) and MySQL (production).
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from dataagent_server.config import get_settings
from dataagent_server.database.models import Base

logger = logging.getLogger(__name__)


class DatabaseFactory:
    """Factory for creating and managing database connections."""
    
    _engine: AsyncEngine | None = None
    _session_factory: async_sessionmaker[AsyncSession] | None = None
    
    @classmethod
    def get_database_url(cls) -> str:
        """Get database URL based on configuration."""
        settings = get_settings()
        
        if settings.session_store == "postgres":
            return settings.postgres_url
        else:
            # SQLite (default for development)
            sqlite_path = Path(settings.sqlite_path)
            sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite+aiosqlite:///{sqlite_path}"
    
    @classmethod
    async def get_engine(cls) -> AsyncEngine:
        """Get or create async database engine."""
        if cls._engine is None:
            url = cls.get_database_url()
            
            settings = get_settings()
            
            if settings.session_store == "postgres":
                cls._engine = create_async_engine(
                    url,
                    pool_size=settings.postgres_pool_size,
                    max_overflow=settings.postgres_max_overflow,
                    pool_pre_ping=True,
                    echo=False,
                )
            else:
                # SQLite
                cls._engine = create_async_engine(
                    url,
                    echo=False,
                    connect_args={"check_same_thread": False},
                )
            
            logger.info(f"Database engine created: {settings.session_store}")
        
        return cls._engine
    
    @classmethod
    async def get_session_factory(cls) -> async_sessionmaker[AsyncSession]:
        """Get or create session factory."""
        if cls._session_factory is None:
            engine = await cls.get_engine()
            cls._session_factory = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
        return cls._session_factory
    
    @classmethod
    async def create_tables(cls) -> None:
        """Create all tables in the database."""
        engine = await cls.get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")
    
    @classmethod
    async def drop_tables(cls) -> None:
        """Drop all tables in the database."""
        engine = await cls.get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped")
    
    @classmethod
    async def close(cls) -> None:
        """Close database connections."""
        if cls._engine is not None:
            await cls._engine.dispose()
            cls._engine = None
            cls._session_factory = None
            logger.info("Database connections closed")


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session context manager.
    
    Usage:
        async with get_db_session() as session:
            # use session
    """
    factory = await DatabaseFactory.get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

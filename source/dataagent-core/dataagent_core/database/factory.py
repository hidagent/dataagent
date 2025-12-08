"""Database factory for creating database connections and stores.

This module provides a unified factory for creating database connections
and store instances for different storage backends.

Usage:
    # Create SQLite stores
    factory = DatabaseFactory.sqlite("~/.dataagent/dataagent.db")
    user_store = await factory.create_user_store()
    session_store = await factory.create_session_store()
    mcp_store = await factory.create_mcp_store()
    
    # Create PostgreSQL stores
    factory = DatabaseFactory.postgres("postgres+aiopostgres://user:pass@localhost/dataagent")
    user_store = await factory.create_user_store()
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

if TYPE_CHECKING:
    from dataagent_core.user.store import UserProfileStore
    from dataagent_core.session.store import SessionStore
    from dataagent_core.session.message_store import MessageStore
    from dataagent_core.mcp.store import MCPConfigStore

logger = logging.getLogger(__name__)


class DatabaseFactory:
    """Factory for creating database connections and stores.
    
    Provides a unified interface for creating different storage backends
    with shared database connections.
    """
    
    def __init__(self, engine: AsyncEngine, dialect: str):
        """Initialize the factory.
        
        Args:
            engine: SQLAlchemy async engine.
            dialect: Database dialect ('sqlite' or 'postgres').
        """
        self._engine = engine
        self._dialect = dialect
        self._initialized = False
    
    @classmethod
    def sqlite(
        cls,
        db_path: str | Path | None = None,
        **engine_kwargs,
    ) -> "DatabaseFactory":
        """Create a factory for SQLite database.
        
        Args:
            db_path: Path to SQLite database file.
                     Defaults to ~/.dataagent/dataagent.db
            **engine_kwargs: Additional arguments for create_async_engine.
            
        Returns:
            DatabaseFactory instance.
        """
        if db_path is None:
            db_path = Path.home() / ".dataagent" / "dataagent.db"
        
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        url = f"sqlite+aiosqlite:///{db_path}"
        engine = create_async_engine(url, echo=False, **engine_kwargs)
        
        logger.info(f"Created SQLite database factory: {db_path}")
        return cls(engine, "sqlite")
    
    @classmethod
    def postgres(
        cls,
        url: str,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_recycle: int = 3600,
        **engine_kwargs,
    ) -> "DatabaseFactory":
        """Create a factory for PostgreSQL database.
        
        Args:
            url: PostgreSQL connection URL.
            pool_size: Connection pool size.
            max_overflow: Maximum overflow connections.
            pool_recycle: Connection recycle time in seconds.
            **engine_kwargs: Additional arguments for create_async_engine.
            
        Returns:
            DatabaseFactory instance.
        """
        engine = create_async_engine(
            url,
            echo=False,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_recycle=pool_recycle,
            **engine_kwargs,
        )
        
        logger.info("Created PostgreSQL database factory")
        return cls(engine, "postgres")
    
    @property
    def engine(self) -> AsyncEngine:
        """Get the SQLAlchemy async engine."""
        return self._engine
    
    @property
    def dialect(self) -> str:
        """Get the database dialect."""
        return self._dialect
    
    async def init_schema(self) -> None:
        """Initialize database schema using migrations.
        
        This applies all pending migrations to bring the database
        to the latest schema version.
        """
        if self._initialized:
            return
        
        from dataagent_core.database.migration import MigrationManager
        
        manager = MigrationManager(self._engine)
        await manager.init()
        await manager.migrate()
        
        self._initialized = True
        logger.info("Database schema initialized")
    
    async def create_user_store(self) -> "UserProfileStore":
        """Create a user profile store.
        
        Returns:
            UserProfileStore instance.
        """
        await self.init_schema()
        
        if self._dialect == "sqlite":
            from dataagent_core.user.sqlite_store import SQLiteUserProfileStore
            store = SQLiteUserProfileStore(engine=self._engine)
        else:
            # PostgreSQL uses the same SQLAlchemy-based store
            from dataagent_core.user.sqlite_store import SQLiteUserProfileStore
            store = SQLiteUserProfileStore(engine=self._engine)
        
        return store
    
    async def create_session_store(self) -> "SessionStore":
        """Create a session store.
        
        Returns:
            SessionStore instance.
        """
        await self.init_schema()
        
        if self._dialect == "sqlite":
            from dataagent_core.session.stores.postgres import PostgreSQLSessionStore
            # PostgreSQLSessionStore works with both PostgreSQL and SQLite via SQLAlchemy
            return PostgreSQLSessionStore(engine=self._engine)
        else:
            from dataagent_core.session.stores.postgres import PostgreSQLSessionStore
            return PostgreSQLSessionStore(engine=self._engine)
    
    async def create_message_store(self) -> "MessageStore":
        """Create a message store.
        
        Returns:
            MessageStore instance.
        """
        await self.init_schema()
        
        from dataagent_core.session.stores.postgres_message import PostgreSQLMessageStore
        return PostgreSQLMessageStore(engine=self._engine)
    
    async def create_mcp_store(self) -> "MCPConfigStore":
        """Create an MCP configuration store.
        
        Returns:
            MCPConfigStore instance.
        """
        await self.init_schema()
        
        if self._dialect == "sqlite":
            from dataagent_core.mcp.sqlite_store import SQLiteMCPConfigStore
            return SQLiteMCPConfigStore(engine=self._engine)
        else:
            from dataagent_core.mcp.store import PostgresMCPConfigStore
            return PostgresMCPConfigStore(engine=self._engine)
    
    async def close(self) -> None:
        """Close the database connection."""
        await self._engine.dispose()
        logger.info("Database connection closed")


# Convenience function for quick setup
async def create_default_factory() -> DatabaseFactory:
    """Create a default database factory using SQLite.
    
    Returns:
        DatabaseFactory instance with SQLite backend.
    """
    factory = DatabaseFactory.sqlite()
    await factory.init_schema()
    return factory

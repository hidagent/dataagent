"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from dataagent_server import __version__
from dataagent_server.api.deps import (
    request_id_middleware,
    setup_exception_handlers,
    set_session_manager,
    set_mcp_store,
)
from dataagent_server.api.v1 import auth, chat, chat_stream, health, sessions, mcp, users, user_profiles, rules, assistants, workspaces, skills
from dataagent_server.config import get_settings
from dataagent_server.ws import ConnectionManager, WebSocketChatHandler
from dataagent_core.session import SessionStoreFactory, MessageStoreFactory
from dataagent_core.config import Settings as CoreSettings
from dataagent_core.engine import AgentFactory
from dataagent_core.mcp import MemoryMCPConfigStore, MCPConnectionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Ensure dataagent modules log at INFO level
logging.getLogger("dataagent_core").setLevel(logging.INFO)
logging.getLogger("dataagent_server").setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager.
    
    Initializes resources on startup and cleans up on shutdown.
    """
    settings = get_settings()
    
    # Initialize server database (s_ tables)
    from dataagent_server.database import DatabaseFactory
    await DatabaseFactory.create_tables()
    logger.info("Server database tables initialized")
    
    # Initialize session store based on configuration
    if settings.session_store == "postgres":
        from dataagent_core.session.stores.postgres import PostgresSessionStore
        from dataagent_core.session.stores.postgres_message import PostgresMessageStore
        from dataagent_core.mcp import PostgresMCPConfigStore
        from dataagent_core.user import MemoryUserProfileStore  # TODO: Add PostgresUserProfileStore
        
        session_store = PostgresSessionStore(
            url=settings.postgres_url,
            pool_size=settings.postgres_pool_size,
            max_overflow=settings.postgres_max_overflow,
        )
        await session_store.init_tables()
        message_store = PostgresMessageStore(engine=session_store._engine)
        mcp_store = PostgresMCPConfigStore(engine=session_store._engine)
        await mcp_store.init_tables()
        user_profile_store = MemoryUserProfileStore()  # TODO: Use Postgres store
        
        logger.info(f"Using PostgreSQL store: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_database}")
        
    elif settings.session_store == "sqlite":
        from dataagent_core.session.stores.sqlite import SQLiteSessionStore
        from dataagent_core.session.stores.sqlite_message import SQLiteMessageStore
        from dataagent_core.mcp import SQLiteMCPConfigStore
        from dataagent_core.user import SQLiteUserProfileStore
        
        session_store = SQLiteSessionStore(db_path=settings.sqlite_path)
        await session_store.init_tables()
        message_store = SQLiteMessageStore(engine=session_store._engine)
        mcp_store = SQLiteMCPConfigStore(engine=session_store._engine)
        await mcp_store.init_tables()
        user_profile_store = SQLiteUserProfileStore(db_path=settings.sqlite_path)
        await user_profile_store.init_tables()
        
        logger.info(f"Using SQLite store: {settings.sqlite_path}")
        
    else:
        from dataagent_core.session import MemorySessionStore, MemoryMessageStore
        from dataagent_core.user import MemoryUserProfileStore
        session_store = MemorySessionStore()
        message_store = MemoryMessageStore()
        mcp_store = MemoryMCPConfigStore()
        user_profile_store = MemoryUserProfileStore()
        logger.info("Using in-memory store")
    
    app.state.session_store = session_store
    app.state.message_store = message_store
    app.state.mcp_store = mcp_store
    app.state.user_profile_store = user_profile_store
    set_mcp_store(mcp_store)
    
    # Initialize connection manager
    app.state.connection_manager = ConnectionManager(
        max_connections=settings.max_connections,
    )
    
    # Initialize core settings and agent factory
    core_settings = CoreSettings.from_environment()
    
    # Create checkpointer for LangGraph state persistence
    # This stores agent execution state (messages, tool calls, etc.)
    # Supported: sqlite, postgres
    checkpointer_cm = None
    checkpointer = None
    
    if settings.session_store == "sqlite":
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
        checkpointer_cm = AsyncSqliteSaver.from_conn_string(settings.sqlite_path)
        checkpointer = await checkpointer_cm.__aenter__()
        logger.info(f"Using SQLite checkpointer: {settings.sqlite_path}")
    
    elif settings.session_store == "postgres":
        # PostgreSQL checkpointer for production
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
            checkpointer_cm = AsyncPostgresSaver.from_conn_string(settings.postgres_url)
            checkpointer = await checkpointer_cm.__aenter__()
            # Setup tables if needed
            await checkpointer.setup()
            logger.info(f"Using PostgreSQL checkpointer: {settings.postgres_host}")
        except ImportError:
            logger.warning("langgraph-checkpoint-postgres not installed, using InMemorySaver")
            from langgraph.checkpoint.memory import InMemorySaver
            checkpointer = InMemorySaver()
    
    agent_factory = AgentFactory(settings=core_settings, checkpointer=checkpointer)
    app.state.agent_factory = agent_factory
    app.state.core_settings = core_settings
    app.state.checkpointer = checkpointer
    app.state.checkpointer_cm = checkpointer_cm
    
    # Initialize MCP connection manager
    mcp_connection_manager = MCPConnectionManager(
        max_connections_per_user=settings.mcp_max_connections_per_user,
        max_total_connections=settings.mcp_max_total_connections,
    )
    app.state.mcp_connection_manager = mcp_connection_manager
    
    # Initialize WebSocket handler with agent factory
    app.state.ws_handler = WebSocketChatHandler(
        connection_manager=app.state.connection_manager,
        agent_factory=agent_factory,
        settings=core_settings,
        mcp_store=mcp_store,
        mcp_connection_manager=mcp_connection_manager,
        user_profile_store=user_profile_store,
        session_store=session_store,
        message_store=message_store,
    )
    
    logger.info(f"DataAgent Server v{__version__} starting...")
    logger.info(f"Listening on {settings.host}:{settings.port}")
    logger.info(f"Max connections: {settings.max_connections}")
    logger.info(f"Default user: {settings.default_user}")
    
    yield
    
    # Cleanup
    await mcp_connection_manager.disconnect_all()
    if checkpointer_cm is not None:
        await checkpointer_cm.__aexit__(None, None, None)
        logger.info("SQLite checkpointer closed")
    if settings.session_store in ("postgres", "sqlite"):
        await session_store.close()
    logger.info("DataAgent Server shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance.
    """
    settings = get_settings()
    
    app = FastAPI(
        title="DataAgent Server",
        description="DataAgent Web Server - REST API and WebSocket service",
        version=__version__,
        lifespan=lifespan,
    )
    
    # Setup CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Setup request ID middleware
    app.add_middleware(BaseHTTPMiddleware, dispatch=request_id_middleware)
    
    # Setup exception handlers
    setup_exception_handlers(app)
    
    # Include API routers
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(chat.router, prefix="/api/v1")
    app.include_router(chat_stream.router, prefix="/api/v1")
    app.include_router(sessions.router, prefix="/api/v1")
    app.include_router(mcp.router, prefix="/api/v1")
    app.include_router(users.router, prefix="/api/v1")
    app.include_router(user_profiles.router, prefix="/api/v1")
    app.include_router(rules.router, prefix="/api/v1")
    app.include_router(assistants.router, prefix="/api/v1")
    app.include_router(workspaces.router, prefix="/api/v1")
    app.include_router(skills.router, prefix="/api/v1")
    
    # WebSocket endpoint
    @app.websocket("/ws/chat/{session_id}")
    async def websocket_chat(websocket: WebSocket, session_id: str):
        """WebSocket endpoint for real-time chat.
        
        Args:
            websocket: WebSocket connection.
            session_id: Session ID for the chat.
        """
        handler = app.state.ws_handler
        await handler.handle_connection(websocket, session_id)
    
    return app


# Create app instance
app = create_app()


def run():
    """Run the server using uvicorn."""
    settings = get_settings()
    uvicorn.run(
        "dataagent_server.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        reload=False,
    )


if __name__ == "__main__":
    run()

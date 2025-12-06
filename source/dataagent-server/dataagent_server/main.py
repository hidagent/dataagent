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
from dataagent_server.api.v1 import chat, health, sessions, mcp, users
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager.
    
    Initializes resources on startup and cleans up on shutdown.
    """
    settings = get_settings()
    
    # Initialize session store based on configuration
    if settings.session_store == "mysql":
        from dataagent_core.session.stores.mysql import MySQLSessionStore
        session_store = MySQLSessionStore(
            url=settings.mysql_url,
            pool_size=settings.mysql_pool_size,
            max_overflow=settings.mysql_max_overflow,
        )
        # Initialize database tables
        await session_store.init_tables()
        
        # Create message store sharing the same engine
        from dataagent_core.session.stores.mysql_message import MySQLMessageStore
        message_store = MySQLMessageStore(engine=session_store._engine)
        
        logger.info(f"Using MySQL session store: {settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database}")
    else:
        from dataagent_core.session import MemorySessionStore, MemoryMessageStore
        session_store = MemorySessionStore()
        message_store = MemoryMessageStore()
        logger.info("Using in-memory session store")
    
    app.state.session_store = session_store
    app.state.message_store = message_store
    
    # Initialize connection manager
    app.state.connection_manager = ConnectionManager(
        max_connections=settings.max_connections,
    )
    
    # Initialize core settings and agent factory
    core_settings = CoreSettings.from_environment()
    agent_factory = AgentFactory(settings=core_settings)
    app.state.agent_factory = agent_factory
    app.state.core_settings = core_settings
    
    # Initialize MCP config store
    if settings.session_store == "mysql":
        from dataagent_core.mcp import MySQLMCPConfigStore
        mcp_store = MySQLMCPConfigStore(engine=session_store._engine)
        await mcp_store.init_tables()
    else:
        mcp_store = MemoryMCPConfigStore()
    
    app.state.mcp_store = mcp_store
    set_mcp_store(mcp_store)
    
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
    )
    
    logger.info(f"DataAgent Server v{__version__} starting...")
    logger.info(f"Listening on {settings.host}:{settings.port}")
    logger.info(f"Max connections: {settings.max_connections}")
    
    yield
    
    # Cleanup
    await mcp_connection_manager.disconnect_all()
    if settings.session_store == "mysql":
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
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(chat.router, prefix="/api/v1")
    app.include_router(sessions.router, prefix="/api/v1")
    app.include_router(mcp.router, prefix="/api/v1")
    app.include_router(users.router, prefix="/api/v1")
    
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

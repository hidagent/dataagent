"""Test configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from dataagent_server.config import ServerSettings
from dataagent_server.main import create_app
from dataagent_server.ws import ConnectionManager


@pytest.fixture
def settings() -> ServerSettings:
    """Create test settings."""
    return ServerSettings(
        host="127.0.0.1",
        port=8000,
        api_keys=["test-key-1", "test-key-2"],
        auth_disabled=False,
        max_connections=10,
    )


@pytest.fixture
def settings_no_auth() -> ServerSettings:
    """Create test settings with auth disabled."""
    return ServerSettings(
        host="127.0.0.1",
        port=8000,
        auth_disabled=True,
    )


@pytest.fixture
def connection_manager() -> ConnectionManager:
    """Create a connection manager for testing."""
    return ConnectionManager(max_connections=10)


@pytest.fixture
def app():
    """Create test FastAPI app with initialized stores."""
    from dataagent_core.session import MemorySessionStore, MemoryMessageStore
    
    app = create_app()
    # Initialize stores for testing (bypassing lifespan)
    app.state.session_store = MemorySessionStore()
    app.state.message_store = MemoryMessageStore()
    app.state.connection_manager = ConnectionManager(max_connections=10)
    return app


@pytest.fixture
def client(app) -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
async def async_client(app) -> AsyncClient:
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

"""Tests for MCP API endpoints.

Tests for /api/v1/users/{user_id}/mcp-servers endpoints.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock

from dataagent_server.main import create_app
from dataagent_server.api.deps import set_mcp_store
from dataagent_core.mcp.config import MCPServerConfig
from dataagent_core.mcp.store import MemoryMCPConfigStore


@pytest.fixture
def mcp_store():
    """Create a memory MCP store for testing."""
    return MemoryMCPConfigStore()


@pytest.fixture
def app(mcp_store):
    """Create test application with MCP store."""
    app = create_app()
    # Set global MCP store
    set_mcp_store(mcp_store)
    # Set MCP connection manager mock
    mock_manager = MagicMock()
    mock_manager.get_connection_status.return_value = {}
    mock_manager.connect = AsyncMock(return_value={})
    mock_manager.disconnect = AsyncMock()
    app.state.mcp_connection_manager = mock_manager
    return app


@pytest.fixture
async def client(app):
    """Create test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestMCPServerListAPI:
    """Tests for GET /api/v1/users/{user_id}/mcp-servers."""

    @pytest.mark.asyncio
    async def test_list_empty(self, client):
        """Test listing servers when none exist."""
        response = await client.get(
            "/api/v1/users/testuser/mcp-servers",
            headers={"X-User-ID": "testuser"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["servers"] == []

    @pytest.mark.asyncio
    async def test_list_servers(self, client, mcp_store):
        """Test listing servers."""
        await mcp_store.add_server("testuser", MCPServerConfig(
            name="server1",
            command="uvx",
            args=["mcp-server-test"],
        ))
        await mcp_store.add_server("testuser", MCPServerConfig(
            name="server2",
            url="http://localhost:8080/mcp",
        ))

        response = await client.get(
            "/api/v1/users/testuser/mcp-servers",
            headers={"X-User-ID": "testuser"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["servers"]) == 2
        names = [s["name"] for s in data["servers"]]
        assert "server1" in names
        assert "server2" in names


class TestMCPServerCreateAPI:
    """Tests for POST /api/v1/users/{user_id}/mcp-servers."""

    @pytest.mark.asyncio
    async def test_create_command_server(self, client):
        """Test creating a command-based server."""
        response = await client.post(
            "/api/v1/users/testuser/mcp-servers",
            headers={"X-User-ID": "testuser"},
            json={
                "name": "filesystem",
                "command": "uvx",
                "args": ["mcp-server-filesystem", "/workspace"],
                "env": {"DEBUG": "true"},
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "filesystem"
        assert data["command"] == "uvx"
        assert data["args"] == ["mcp-server-filesystem", "/workspace"]
        assert data["env"] == {"DEBUG": "true"}

    @pytest.mark.asyncio
    async def test_create_url_server(self, client):
        """Test creating a URL-based server."""
        response = await client.post(
            "/api/v1/users/testuser/mcp-servers",
            headers={"X-User-ID": "testuser"},
            json={
                "name": "remote",
                "url": "http://localhost:8080/mcp",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "remote"
        assert data["url"] == "http://localhost:8080/mcp"
        assert data["transport"] == "sse"  # Default

    @pytest.mark.asyncio
    async def test_create_server_with_transport(self, client):
        """Test creating server with transport type."""
        response = await client.post(
            "/api/v1/users/testuser/mcp-servers",
            headers={"X-User-ID": "testuser"},
            json={
                "name": "remote",
                "url": "http://localhost:8080/mcp",
                "transport": "streamable_http",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["transport"] == "streamable_http"

    @pytest.mark.asyncio
    async def test_create_server_with_headers(self, client):
        """Test creating server with custom headers."""
        headers = {
            "X-API-Key": "secret-key",
            "X-User-Token": "token123",
        }
        response = await client.post(
            "/api/v1/users/testuser/mcp-servers",
            headers={"X-User-ID": "testuser"},
            json={
                "name": "remote",
                "url": "http://localhost:8080/mcp",
                "headers": headers,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["headers"] == headers

    @pytest.mark.asyncio
    async def test_create_server_full_config(self, client):
        """Test creating server with all options."""
        response = await client.post(
            "/api/v1/users/testuser/mcp-servers",
            headers={"X-User-ID": "testuser"},
            json={
                "name": "full-config",
                "url": "http://10.21.19.93:9042/mcp",
                "transport": "streamable_http",
                "headers": {
                    "X-User-Token": "token123",
                    "X-Database-Host": "db.example.com",
                },
                "disabled": False,
                "autoApprove": ["query_sql"],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["url"] == "http://10.21.19.93:9042/mcp"
        assert data["transport"] == "streamable_http"
        assert data["headers"]["X-User-Token"] == "token123"


class TestMCPServerGetAPI:
    """Tests for GET /api/v1/users/{user_id}/mcp-servers/{server_name}."""

    @pytest.mark.asyncio
    async def test_get_server(self, client, mcp_store):
        """Test getting a specific server."""
        await mcp_store.add_server("testuser", MCPServerConfig(
            name="test",
            url="http://localhost:8080/mcp",
            transport="streamable_http",
            headers={"X-Key": "value"},
        ))

        response = await client.get(
            "/api/v1/users/testuser/mcp-servers/test",
            headers={"X-User-ID": "testuser"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test"
        assert data["url"] == "http://localhost:8080/mcp"

    @pytest.mark.asyncio
    async def test_get_nonexistent_server(self, client):
        """Test getting nonexistent server returns 404."""
        response = await client.get(
            "/api/v1/users/testuser/mcp-servers/nonexistent",
            headers={"X-User-ID": "testuser"},
        )
        assert response.status_code == 404


class TestMCPServerUpdateAPI:
    """Tests for PUT /api/v1/users/{user_id}/mcp-servers/{server_name}."""

    @pytest.mark.asyncio
    async def test_update_server(self, client, mcp_store):
        """Test updating a server."""
        await mcp_store.add_server("testuser", MCPServerConfig(
            name="test",
            url="http://localhost:8080/mcp",
        ))

        response = await client.put(
            "/api/v1/users/testuser/mcp-servers/test",
            headers={"X-User-ID": "testuser"},
            json={
                "name": "test",
                "url": "http://localhost:9090/mcp",
                "transport": "streamable_http",
                "headers": {"X-New-Key": "new-value"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["url"] == "http://localhost:9090/mcp"
        assert data["transport"] == "streamable_http"
        assert data["headers"] == {"X-New-Key": "new-value"}

    @pytest.mark.asyncio
    async def test_update_nonexistent_server(self, client):
        """Test updating nonexistent server returns 404."""
        response = await client.put(
            "/api/v1/users/testuser/mcp-servers/nonexistent",
            headers={"X-User-ID": "testuser"},
            json={
                "name": "nonexistent",
                "command": "uvx",
            },
        )
        assert response.status_code == 404


class TestMCPServerDeleteAPI:
    """Tests for DELETE /api/v1/users/{user_id}/mcp-servers/{server_name}."""

    @pytest.mark.asyncio
    async def test_delete_server(self, client, mcp_store):
        """Test deleting a server."""
        await mcp_store.add_server("testuser", MCPServerConfig(
            name="test",
            command="uvx",
        ))

        response = await client.delete(
            "/api/v1/users/testuser/mcp-servers/test",
            headers={"X-User-ID": "testuser"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify deleted
        server = await mcp_store.get_server("testuser", "test")
        assert server is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_server(self, client):
        """Test deleting nonexistent server returns 404."""
        response = await client.delete(
            "/api/v1/users/testuser/mcp-servers/nonexistent",
            headers={"X-User-ID": "testuser"},
        )
        assert response.status_code == 404


class TestMCPServerToggleAPI:
    """Tests for POST /api/v1/users/{user_id}/mcp-servers/{server_name}/toggle."""

    @pytest.mark.asyncio
    async def test_disable_server(self, client, mcp_store):
        """Test disabling a server."""
        await mcp_store.add_server("testuser", MCPServerConfig(
            name="test",
            command="uvx",
            disabled=False,
        ))

        response = await client.post(
            "/api/v1/users/testuser/mcp-servers/test/toggle",
            headers={"X-User-ID": "testuser"},
            json={"disabled": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["disabled"] is True

    @pytest.mark.asyncio
    async def test_enable_server(self, client, mcp_store):
        """Test enabling a server."""
        await mcp_store.add_server("testuser", MCPServerConfig(
            name="test",
            command="uvx",
            disabled=True,
        ))

        response = await client.post(
            "/api/v1/users/testuser/mcp-servers/test/toggle",
            headers={"X-User-ID": "testuser"},
            json={"disabled": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["disabled"] is False


class TestMCPServerConnectAPI:
    """Tests for POST /api/v1/users/{user_id}/mcp-servers/{server_name}/connect."""

    @pytest.mark.asyncio
    async def test_connect_disabled_server(self, client, mcp_store):
        """Test connecting to disabled server returns error."""
        await mcp_store.add_server("testuser", MCPServerConfig(
            name="test",
            command="uvx",
            disabled=True,
        ))

        response = await client.post(
            "/api/v1/users/testuser/mcp-servers/test/connect",
            headers={"X-User-ID": "testuser"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["status"] == "disabled"

    @pytest.mark.asyncio
    async def test_connect_nonexistent_server(self, client):
        """Test connecting to nonexistent server returns 404."""
        response = await client.post(
            "/api/v1/users/testuser/mcp-servers/nonexistent/connect",
            headers={"X-User-ID": "testuser"},
        )
        assert response.status_code == 404


class TestMCPServerStatusAPI:
    """Tests for GET /api/v1/users/{user_id}/mcp-servers/{server_name}/status."""

    @pytest.mark.asyncio
    async def test_get_status(self, client, mcp_store):
        """Test getting server status."""
        await mcp_store.add_server("testuser", MCPServerConfig(
            name="test",
            command="uvx",
        ))

        response = await client.get(
            "/api/v1/users/testuser/mcp-servers/test/status",
            headers={"X-User-ID": "testuser"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test"
        assert "status" in data
        assert "connected" in data

    @pytest.mark.asyncio
    async def test_get_status_nonexistent(self, client):
        """Test getting status of nonexistent server returns 404."""
        response = await client.get(
            "/api/v1/users/testuser/mcp-servers/nonexistent/status",
            headers={"X-User-ID": "testuser"},
        )
        assert response.status_code == 404


class TestMCPAPIUserIsolation:
    """Tests for user isolation in MCP API."""

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_user_servers(self, client, mcp_store):
        """Test user cannot access another user's servers."""
        await mcp_store.add_server("user1", MCPServerConfig(
            name="secret",
            url="http://secret.example.com/mcp",
        ))

        # user2 tries to access user1's server
        response = await client.get(
            "/api/v1/users/user1/mcp-servers/secret",
            headers={"X-User-ID": "user2"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_user_can_access_own_servers(self, client, mcp_store):
        """Test user can access their own servers."""
        await mcp_store.add_server("testuser", MCPServerConfig(
            name="myserver",
            url="http://localhost:8080/mcp",
        ))

        response = await client.get(
            "/api/v1/users/testuser/mcp-servers/myserver",
            headers={"X-User-ID": "testuser"},
        )
        assert response.status_code == 200

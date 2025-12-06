"""Extended tests for MCP connection manager.

Tests for MCPConnectionManager with transport, headers support.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from dataagent_core.mcp.config import MCPServerConfig, MCPConfig
from dataagent_core.mcp.manager import MCPConnectionManager, MCPConnection


class TestMCPConnectionManagerBasic:
    """Basic tests for MCPConnectionManager."""

    def test_init(self):
        """Test manager initialization."""
        manager = MCPConnectionManager(
            max_connections_per_user=5,
            max_total_connections=50,
        )
        assert manager.max_connections_per_user == 5
        assert manager.max_total_connections == 50
        assert manager.total_connections == 0
        assert manager.get_user_count() == 0

    @pytest.mark.asyncio
    async def test_get_tools_no_connections(self):
        """Test getting tools when no connections exist."""
        manager = MCPConnectionManager()
        tools = manager.get_tools("user1")
        assert tools == []

    @pytest.mark.asyncio
    async def test_get_connection_status_no_connections(self):
        """Test getting status when no connections exist."""
        manager = MCPConnectionManager()
        status = manager.get_connection_status("user1")
        assert status == {}

    @pytest.mark.asyncio
    async def test_disconnect_no_connections(self):
        """Test disconnecting when no connections exist."""
        manager = MCPConnectionManager()
        # Should not raise
        await manager.disconnect("user1")
        await manager.disconnect("user1", "server1")


class TestMCPConnectionManagerConnect:
    """Tests for MCPConnectionManager.connect()."""

    @pytest.mark.asyncio
    async def test_connect_without_mcp_adapters(self):
        """Test connect when langchain-mcp-adapters is not installed."""
        manager = MCPConnectionManager()
        config = MCPConfig()
        config.add_server(MCPServerConfig(
            name="test",
            command="uvx",
            args=["test-server"],
        ))

        with patch.dict("sys.modules", {"langchain_mcp_adapters": None}):
            with patch("dataagent_core.mcp.manager.MCPConnectionManager._create_connection") as mock:
                # Simulate ImportError
                connection = MCPConnection(server_config=config.servers["test"])
                connection.error = "langchain-mcp-adapters not installed"
                mock.return_value = connection

                connections = await manager.connect("user1", config)
                assert "test" in connections
                assert connections["test"].error is not None

    @pytest.mark.asyncio
    async def test_connect_respects_max_connections_per_user(self):
        """Test connect respects max connections per user limit."""
        manager = MCPConnectionManager(max_connections_per_user=2)
        config = MCPConfig()
        for i in range(5):
            config.add_server(MCPServerConfig(name=f"server{i}", command="uvx"))

        with patch.object(manager, "_create_connection") as mock:
            mock.return_value = MCPConnection(
                server_config=config.servers["server0"],
                connected=True,
            )
            connections = await manager.connect("user1", config)
            # Should only connect up to max_connections_per_user
            assert len(connections) <= 2

    @pytest.mark.asyncio
    async def test_connect_skips_disabled_servers(self):
        """Test connect skips disabled servers."""
        manager = MCPConnectionManager()
        config = MCPConfig()
        config.add_server(MCPServerConfig(name="enabled", command="uvx"))
        config.add_server(MCPServerConfig(name="disabled", command="uvx", disabled=True))

        with patch.object(manager, "_create_connection") as mock:
            mock.return_value = MCPConnection(
                server_config=config.servers["enabled"],
                connected=True,
            )
            connections = await manager.connect("user1", config)
            # Should only try to connect enabled server
            assert mock.call_count == 1

    @pytest.mark.asyncio
    async def test_connect_skips_already_connected(self):
        """Test connect skips already connected servers."""
        manager = MCPConnectionManager()
        config = MCPConfig()
        config.add_server(MCPServerConfig(name="test", command="uvx"))

        # First connection
        with patch.object(manager, "_create_connection") as mock:
            connection = MCPConnection(
                server_config=config.servers["test"],
                connected=True,
            )
            mock.return_value = connection
            await manager.connect("user1", config)
            assert mock.call_count == 1

            # Second connection attempt should skip
            await manager.connect("user1", config)
            assert mock.call_count == 1  # Still 1, not called again


class TestMCPConnectionManagerCreateConnection:
    """Tests for MCPConnectionManager._create_connection()."""

    @pytest.mark.asyncio
    async def test_create_connection_url_server(self):
        """Test creating connection for URL-based server."""
        manager = MCPConnectionManager()
        server_config = MCPServerConfig(
            name="remote",
            url="http://localhost:8080/mcp",
            transport="streamable_http",
            headers={"X-Key": "value"},
        )

        # Mock the MCP client - patch where it's imported
        with patch("langchain_mcp_adapters.client.MultiServerMCPClient") as MockClient:
            mock_client = MagicMock()
            mock_client.get_tools = AsyncMock(return_value=[
                MagicMock(name="tool1"),
                MagicMock(name="tool2"),
            ])
            MockClient.return_value = mock_client

            connection = await manager._create_connection(server_config)

            # Verify client was created with correct config
            MockClient.assert_called_once()
            call_args = MockClient.call_args[0][0]
            assert "remote" in call_args
            assert call_args["remote"]["url"] == "http://localhost:8080/mcp"
            assert call_args["remote"]["transport"] == "streamable_http"
            assert call_args["remote"]["headers"] == {"X-Key": "value"}

    @pytest.mark.asyncio
    async def test_create_connection_command_server(self):
        """Test creating connection for command-based server."""
        manager = MCPConnectionManager()
        server_config = MCPServerConfig(
            name="local",
            command="uvx",
            args=["mcp-server-test"],
            env={"DEBUG": "true"},
        )

        with patch("langchain_mcp_adapters.client.MultiServerMCPClient") as MockClient:
            mock_client = MagicMock()
            mock_client.get_tools = AsyncMock(return_value=[])
            MockClient.return_value = mock_client

            await manager._create_connection(server_config)

            call_args = MockClient.call_args[0][0]
            assert call_args["local"]["command"] == "uvx"
            assert call_args["local"]["args"] == ["mcp-server-test"]
            assert call_args["local"]["env"] == {"DEBUG": "true"}

    @pytest.mark.asyncio
    async def test_create_connection_handles_exception(self):
        """Test connection handles exceptions gracefully."""
        manager = MCPConnectionManager()
        server_config = MCPServerConfig(
            name="failing",
            url="http://localhost:8080/mcp",
        )

        with patch("langchain_mcp_adapters.client.MultiServerMCPClient") as MockClient:
            mock_client = MagicMock()
            mock_client.get_tools = AsyncMock(side_effect=Exception("Connection failed"))
            MockClient.return_value = mock_client

            connection = await manager._create_connection(server_config)

            assert connection.connected is False
            assert connection.error is not None
            assert "Connection failed" in connection.error


class TestMCPConnectionManagerDisconnect:
    """Tests for MCPConnectionManager.disconnect()."""

    @pytest.mark.asyncio
    async def test_disconnect_specific_server(self):
        """Test disconnecting a specific server."""
        manager = MCPConnectionManager()

        # Setup mock connection
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        connection = MCPConnection(
            server_config=MCPServerConfig(name="test", command="uvx"),
            client=mock_client,
            connected=True,
        )
        manager._connections["user1"] = {"test": connection}
        manager._total_connections = 1

        await manager.disconnect("user1", "test")

        assert "test" not in manager._connections.get("user1", {})
        assert manager._total_connections == 0

    @pytest.mark.asyncio
    async def test_disconnect_all_user_servers(self):
        """Test disconnecting all servers for a user."""
        manager = MCPConnectionManager()

        # Setup mock connections
        for name in ["server1", "server2"]:
            mock_client = MagicMock()
            mock_client.close = AsyncMock()
            connection = MCPConnection(
                server_config=MCPServerConfig(name=name, command="uvx"),
                client=mock_client,
                connected=True,
            )
            if "user1" not in manager._connections:
                manager._connections["user1"] = {}
            manager._connections["user1"][name] = connection
            manager._total_connections += 1

        await manager.disconnect("user1")

        assert "user1" not in manager._connections
        assert manager._total_connections == 0

    @pytest.mark.asyncio
    async def test_disconnect_all(self):
        """Test disconnecting all connections."""
        manager = MCPConnectionManager()

        # Setup connections for multiple users
        for user in ["user1", "user2"]:
            mock_client = MagicMock()
            mock_client.close = AsyncMock()
            connection = MCPConnection(
                server_config=MCPServerConfig(name="test", command="uvx"),
                client=mock_client,
                connected=True,
            )
            manager._connections[user] = {"test": connection}
            manager._total_connections += 1

        await manager.disconnect_all()

        assert manager._connections == {}
        assert manager._total_connections == 0


class TestMCPConnectionManagerStatus:
    """Tests for MCPConnectionManager status methods."""

    def test_get_connection_status(self):
        """Test getting connection status."""
        manager = MCPConnectionManager()

        # Setup mock connection
        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        connection = MCPConnection(
            server_config=MCPServerConfig(name="test", command="uvx"),
            connected=True,
            tools=[mock_tool],
        )
        manager._connections["user1"] = {"test": connection}

        status = manager.get_connection_status("user1")

        assert "test" in status
        assert status["test"]["connected"] is True
        assert status["test"]["tools_count"] == 1
        assert status["test"]["error"] is None

    def test_get_connection_status_with_error(self):
        """Test getting connection status with error."""
        manager = MCPConnectionManager()

        connection = MCPConnection(
            server_config=MCPServerConfig(name="test", command="uvx"),
            connected=False,
            error="Connection failed",
        )
        manager._connections["user1"] = {"test": connection}

        status = manager.get_connection_status("user1")

        assert status["test"]["connected"] is False
        assert status["test"]["error"] == "Connection failed"

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check."""
        manager = MCPConnectionManager()

        # Setup connections
        healthy = MCPConnection(
            server_config=MCPServerConfig(name="healthy", command="uvx"),
            client=MagicMock(),
            connected=True,
        )
        unhealthy = MCPConnection(
            server_config=MCPServerConfig(name="unhealthy", command="uvx"),
            connected=False,
        )
        manager._connections["user1"] = {
            "healthy": healthy,
            "unhealthy": unhealthy,
        }

        health = await manager.health_check("user1")

        assert health["healthy"] is True
        assert health["unhealthy"] is False


class TestMCPConnectionManagerUserIsolation:
    """Tests for user isolation in MCPConnectionManager."""

    def test_get_tools_isolated(self):
        """Test tools are isolated per user."""
        manager = MCPConnectionManager()

        # Setup tools for different users
        tool1 = MagicMock()
        tool1.name = "user1_tool"
        tool2 = MagicMock()
        tool2.name = "user2_tool"

        manager._connections["user1"] = {
            "server": MCPConnection(
                server_config=MCPServerConfig(name="server", command="uvx"),
                connected=True,
                tools=[tool1],
            )
        }
        manager._connections["user2"] = {
            "server": MCPConnection(
                server_config=MCPServerConfig(name="server", command="uvx"),
                connected=True,
                tools=[tool2],
            )
        }

        user1_tools = manager.get_tools("user1")
        user2_tools = manager.get_tools("user2")

        assert len(user1_tools) == 1
        assert user1_tools[0].name == "user1_tool"
        assert len(user2_tools) == 1
        assert user2_tools[0].name == "user2_tool"

    def test_get_connection_status_isolated(self):
        """Test connection status is isolated per user."""
        manager = MCPConnectionManager()

        manager._connections["user1"] = {
            "server1": MCPConnection(
                server_config=MCPServerConfig(name="server1", command="uvx"),
                connected=True,
            )
        }
        manager._connections["user2"] = {
            "server2": MCPConnection(
                server_config=MCPServerConfig(name="server2", command="uvx"),
                connected=True,
            )
        }

        status1 = manager.get_connection_status("user1")
        status2 = manager.get_connection_status("user2")

        assert "server1" in status1
        assert "server2" not in status1
        assert "server2" in status2
        assert "server1" not in status2

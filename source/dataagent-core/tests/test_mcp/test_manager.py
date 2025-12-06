"""Tests for MCP connection manager.

Property 50: MCP 连接池资源释放
"""

import pytest

from dataagent_core.mcp.config import MCPConfig, MCPServerConfig
from dataagent_core.mcp.manager import MCPConnectionManager, MCPConnection


class TestMCPConnectionManager:
    """Tests for MCPConnectionManager."""

    def test_init_defaults(self):
        """Test default initialization."""
        manager = MCPConnectionManager()
        assert manager.max_connections_per_user == 10
        assert manager.max_total_connections == 100
        assert manager.total_connections == 0
        assert manager.get_user_count() == 0

    def test_init_custom_limits(self):
        """Test custom connection limits."""
        manager = MCPConnectionManager(
            max_connections_per_user=5,
            max_total_connections=50,
        )
        assert manager.max_connections_per_user == 5
        assert manager.max_total_connections == 50

    def test_get_tools_no_connections(self):
        """Test getting tools when no connections exist."""
        manager = MCPConnectionManager()
        tools = manager.get_tools("user1")
        assert tools == []

    def test_get_connection_status_no_connections(self):
        """Test getting status when no connections exist."""
        manager = MCPConnectionManager()
        status = manager.get_connection_status("user1")
        assert status == {}

    @pytest.mark.asyncio
    async def test_health_check_no_connections(self):
        """Test health check when no connections exist."""
        manager = MCPConnectionManager()
        health = await manager.health_check("user1")
        assert health == {}

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_user(self):
        """Test disconnecting nonexistent user doesn't raise."""
        manager = MCPConnectionManager()
        # Should not raise
        await manager.disconnect("nonexistent-user")

    @pytest.mark.asyncio
    async def test_disconnect_all_empty(self):
        """Test disconnecting all when empty doesn't raise."""
        manager = MCPConnectionManager()
        # Should not raise
        await manager.disconnect_all()


class TestMCPConnectionManagerResourceRelease:
    """Tests for MCP connection pool resource release.
    
    Property 50: MCP 连接池资源释放
    """

    @pytest.mark.asyncio
    async def test_disconnect_removes_connection_entry(self):
        """Property 50: 断开连接移除连接条目."""
        manager = MCPConnectionManager()
        
        # Manually add a mock connection to test cleanup
        user_id = "test-user"
        manager._connections[user_id] = {
            "server1": MCPConnection(
                server_config=MCPServerConfig(name="server1", command="test"),
                connected=False,  # Not actually connected (no client)
            ),
        }
        
        # Disconnect
        await manager.disconnect(user_id)
        
        # Verify connection entry removed
        assert user_id not in manager._connections

    @pytest.mark.asyncio
    async def test_disconnect_specific_server_removes_entry(self):
        """Property 50: 断开特定服务器移除条目."""
        manager = MCPConnectionManager()
        
        user_id = "test-user"
        manager._connections[user_id] = {
            "server1": MCPConnection(
                server_config=MCPServerConfig(name="server1", command="test"),
                connected=False,
            ),
            "server2": MCPConnection(
                server_config=MCPServerConfig(name="server2", command="test"),
                connected=False,
            ),
        }
        
        # Disconnect only server1
        await manager.disconnect(user_id, "server1")
        
        # Verify partial cleanup
        assert user_id in manager._connections
        assert "server1" not in manager._connections[user_id]
        assert "server2" in manager._connections[user_id]

    @pytest.mark.asyncio
    async def test_disconnect_all_clears_all_entries(self):
        """Property 50: disconnect_all 清除所有条目."""
        manager = MCPConnectionManager()
        
        # Add connections for multiple users
        for i in range(3):
            user_id = f"user-{i}"
            manager._connections[user_id] = {
                "server": MCPConnection(
                    server_config=MCPServerConfig(name="server", command="test"),
                    connected=False,
                ),
            }
        
        # Disconnect all
        await manager.disconnect_all()
        
        # Verify all cleaned up
        assert len(manager._connections) == 0
        assert manager.get_user_count() == 0

    @pytest.mark.asyncio
    async def test_disconnect_decrements_total_for_connected(self):
        """Property 50: 断开已连接的服务器减少计数."""
        manager = MCPConnectionManager()
        
        user_id = "test-user"
        # Simulate a connected server (with client)
        connection = MCPConnection(
            server_config=MCPServerConfig(name="server1", command="test"),
            connected=True,
            client=None,  # No actual client, but marked as connected
        )
        manager._connections[user_id] = {"server1": connection}
        manager._total_connections = 1
        
        # Disconnect
        await manager.disconnect(user_id)
        
        # Total should be decremented
        assert manager.total_connections == 0

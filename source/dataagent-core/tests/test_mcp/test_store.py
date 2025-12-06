"""Tests for MCP configuration storage.

Property 49: 用户 MCP 配置隔离
"""

import pytest

from dataagent_core.mcp.config import MCPServerConfig
from dataagent_core.mcp.store import MemoryMCPConfigStore


class TestMemoryMCPConfigStore:
    """Tests for MemoryMCPConfigStore."""

    @pytest.mark.asyncio
    async def test_get_empty_config(self):
        """Test getting config for user with no config."""
        store = MemoryMCPConfigStore()
        config = await store.get_user_config("user1")
        assert config.servers == {}

    @pytest.mark.asyncio
    async def test_add_server(self):
        """Test adding a server."""
        store = MemoryMCPConfigStore()
        server = MCPServerConfig(name="test", command="uvx")
        
        await store.add_server("user1", server)
        
        config = await store.get_user_config("user1")
        assert "test" in config.servers
        assert config.servers["test"].command == "uvx"

    @pytest.mark.asyncio
    async def test_remove_server(self):
        """Test removing a server."""
        store = MemoryMCPConfigStore()
        server = MCPServerConfig(name="test", command="uvx")
        await store.add_server("user1", server)
        
        result = await store.remove_server("user1", "test")
        assert result is True
        
        config = await store.get_user_config("user1")
        assert "test" not in config.servers

    @pytest.mark.asyncio
    async def test_remove_nonexistent_server(self):
        """Test removing nonexistent server returns False."""
        store = MemoryMCPConfigStore()
        result = await store.remove_server("user1", "nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_server(self):
        """Test getting a specific server."""
        store = MemoryMCPConfigStore()
        server = MCPServerConfig(name="test", command="uvx", args=["arg1"])
        await store.add_server("user1", server)
        
        result = await store.get_server("user1", "test")
        assert result is not None
        assert result.name == "test"
        assert result.args == ["arg1"]

    @pytest.mark.asyncio
    async def test_get_nonexistent_server(self):
        """Test getting nonexistent server returns None."""
        store = MemoryMCPConfigStore()
        result = await store.get_server("user1", "nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_user_config(self):
        """Test deleting all config for a user."""
        store = MemoryMCPConfigStore()
        await store.add_server("user1", MCPServerConfig(name="s1", command="uvx"))
        await store.add_server("user1", MCPServerConfig(name="s2", command="npx"))
        
        result = await store.delete_user_config("user1")
        assert result is True
        
        config = await store.get_user_config("user1")
        assert config.servers == {}

    @pytest.mark.asyncio
    async def test_delete_nonexistent_user_config(self):
        """Test deleting config for user with no config."""
        store = MemoryMCPConfigStore()
        result = await store.delete_user_config("nonexistent")
        assert result is False


class TestMCPConfigIsolation:
    """Tests for user MCP configuration isolation.
    
    Property 49: 用户 MCP 配置隔离
    """

    @pytest.mark.asyncio
    async def test_user_configs_isolated(self):
        """Property 49: 不同用户的配置相互隔离."""
        store = MemoryMCPConfigStore()
        
        # Add different configs for different users
        await store.add_server("user1", MCPServerConfig(
            name="filesystem",
            command="uvx",
            args=["mcp-server-filesystem", "/user1/workspace"],
        ))
        await store.add_server("user2", MCPServerConfig(
            name="filesystem",
            command="uvx",
            args=["mcp-server-filesystem", "/user2/workspace"],
        ))
        
        # Verify isolation
        config1 = await store.get_user_config("user1")
        config2 = await store.get_user_config("user2")
        
        assert config1.servers["filesystem"].args[1] == "/user1/workspace"
        assert config2.servers["filesystem"].args[1] == "/user2/workspace"

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_user_config(self):
        """Property 49: 用户只能访问自己的配置."""
        store = MemoryMCPConfigStore()
        
        # Add config for user1
        await store.add_server("user1", MCPServerConfig(
            name="secret-server",
            command="uvx",
            env={"API_KEY": "user1-secret"},
        ))
        
        # user2 should not see user1's config
        config2 = await store.get_user_config("user2")
        assert "secret-server" not in config2.servers
        
        server = await store.get_server("user2", "secret-server")
        assert server is None

    @pytest.mark.asyncio
    async def test_delete_user_config_does_not_affect_others(self):
        """Property 49: 删除用户配置不影响其他用户."""
        store = MemoryMCPConfigStore()
        
        # Add configs for both users
        await store.add_server("user1", MCPServerConfig(name="s1", command="uvx"))
        await store.add_server("user2", MCPServerConfig(name="s2", command="npx"))
        
        # Delete user1's config
        await store.delete_user_config("user1")
        
        # user2's config should still exist
        config2 = await store.get_user_config("user2")
        assert "s2" in config2.servers

    @pytest.mark.asyncio
    async def test_multiple_servers_per_user(self):
        """Property 49: 每个用户可以有多个服务器配置."""
        store = MemoryMCPConfigStore()
        
        # Add multiple servers for one user
        await store.add_server("user1", MCPServerConfig(name="filesystem", command="uvx"))
        await store.add_server("user1", MCPServerConfig(name="database", command="npx"))
        await store.add_server("user1", MCPServerConfig(name="custom", command="python"))
        
        config = await store.get_user_config("user1")
        assert len(config.servers) == 3
        assert "filesystem" in config.servers
        assert "database" in config.servers
        assert "custom" in config.servers

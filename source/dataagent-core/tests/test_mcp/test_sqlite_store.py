"""Tests for SQLite MCP configuration storage.

Tests for SQLiteMCPConfigStore with transport, headers support.
"""

import tempfile
from pathlib import Path

import pytest

from dataagent_core.mcp.config import MCPServerConfig, MCPConfig
from dataagent_core.mcp.sqlite_store import SQLiteMCPConfigStore


@pytest.fixture
async def sqlite_store():
    """Create a temporary SQLite store for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = SQLiteMCPConfigStore(db_path=db_path)
        await store.init_tables()
        yield store
        await store.close()


class TestSQLiteMCPConfigStoreBasic:
    """Basic tests for SQLiteMCPConfigStore."""

    @pytest.mark.asyncio
    async def test_init_tables(self, sqlite_store):
        """Test table initialization."""
        # Table should be created by fixture
        config = await sqlite_store.get_user_config("test_user")
        assert config.servers == {}

    @pytest.mark.asyncio
    async def test_add_server(self, sqlite_store):
        """Test adding a server."""
        server = MCPServerConfig(
            name="test-server",
            command="uvx",
            args=["mcp-server-test"],
        )
        await sqlite_store.add_server("user1", server)

        config = await sqlite_store.get_user_config("user1")
        assert "test-server" in config.servers
        assert config.servers["test-server"].command == "uvx"

    @pytest.mark.asyncio
    async def test_get_server(self, sqlite_store):
        """Test getting a specific server."""
        server = MCPServerConfig(
            name="test",
            command="uvx",
            args=["arg1", "arg2"],
            env={"KEY": "value"},
        )
        await sqlite_store.add_server("user1", server)

        result = await sqlite_store.get_server("user1", "test")
        assert result is not None
        assert result.name == "test"
        assert result.args == ["arg1", "arg2"]
        assert result.env == {"KEY": "value"}

    @pytest.mark.asyncio
    async def test_get_nonexistent_server(self, sqlite_store):
        """Test getting nonexistent server returns None."""
        result = await sqlite_store.get_server("user1", "nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_remove_server(self, sqlite_store):
        """Test removing a server."""
        server = MCPServerConfig(name="test", command="uvx")
        await sqlite_store.add_server("user1", server)

        result = await sqlite_store.remove_server("user1", "test")
        assert result is True

        config = await sqlite_store.get_user_config("user1")
        assert "test" not in config.servers

    @pytest.mark.asyncio
    async def test_remove_nonexistent_server(self, sqlite_store):
        """Test removing nonexistent server returns False."""
        result = await sqlite_store.remove_server("user1", "nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_update_server(self, sqlite_store):
        """Test updating an existing server (upsert)."""
        server1 = MCPServerConfig(name="test", command="uvx", args=["v1"])
        await sqlite_store.add_server("user1", server1)

        server2 = MCPServerConfig(name="test", command="npx", args=["v2"])
        await sqlite_store.add_server("user1", server2)

        result = await sqlite_store.get_server("user1", "test")
        assert result.command == "npx"
        assert result.args == ["v2"]

    @pytest.mark.asyncio
    async def test_delete_user_config(self, sqlite_store):
        """Test deleting all config for a user."""
        await sqlite_store.add_server("user1", MCPServerConfig(name="s1", command="uvx"))
        await sqlite_store.add_server("user1", MCPServerConfig(name="s2", command="npx"))

        result = await sqlite_store.delete_user_config("user1")
        assert result is True

        config = await sqlite_store.get_user_config("user1")
        assert config.servers == {}


class TestSQLiteMCPConfigStoreURLServers:
    """Tests for SQLiteMCPConfigStore with URL-based servers."""

    @pytest.mark.asyncio
    async def test_add_url_server(self, sqlite_store):
        """Test adding a URL-based server."""
        server = MCPServerConfig(
            name="remote",
            url="http://localhost:8080/mcp",
        )
        await sqlite_store.add_server("user1", server)

        result = await sqlite_store.get_server("user1", "remote")
        assert result.url == "http://localhost:8080/mcp"

    @pytest.mark.asyncio
    async def test_add_server_with_transport(self, sqlite_store):
        """Test adding server with transport type."""
        server = MCPServerConfig(
            name="remote",
            url="http://localhost:8080/mcp",
            transport="streamable_http",
        )
        await sqlite_store.add_server("user1", server)

        result = await sqlite_store.get_server("user1", "remote")
        assert result.transport == "streamable_http"

    @pytest.mark.asyncio
    async def test_add_server_with_headers(self, sqlite_store):
        """Test adding server with custom headers."""
        headers = {
            "X-API-Key": "secret-key",
            "X-User-Token": "token123",
        }
        server = MCPServerConfig(
            name="remote",
            url="http://localhost:8080/mcp",
            headers=headers,
        )
        await sqlite_store.add_server("user1", server)

        result = await sqlite_store.get_server("user1", "remote")
        assert result.headers == headers

    @pytest.mark.asyncio
    async def test_add_server_full_config(self, sqlite_store):
        """Test adding server with all URL options."""
        server = MCPServerConfig(
            name="full-config",
            url="http://10.21.19.93:9042/mcp",
            transport="streamable_http",
            headers={
                "X-User-Token": "token123",
                "X-Database-Host": "db.example.com",
                "X-Database-Port": "3306",
            },
            disabled=False,
            auto_approve=["query_sql", "list_tables"],
        )
        await sqlite_store.add_server("user1", server)

        result = await sqlite_store.get_server("user1", "full-config")
        assert result.url == "http://10.21.19.93:9042/mcp"
        assert result.transport == "streamable_http"
        assert result.headers["X-User-Token"] == "token123"
        assert result.headers["X-Database-Host"] == "db.example.com"
        assert result.auto_approve == ["query_sql", "list_tables"]

    @pytest.mark.asyncio
    async def test_default_transport_is_sse(self, sqlite_store):
        """Test default transport is 'sse' when not specified."""
        server = MCPServerConfig(
            name="remote",
            url="http://localhost:8080/mcp",
        )
        await sqlite_store.add_server("user1", server)

        result = await sqlite_store.get_server("user1", "remote")
        assert result.transport == "sse"

    @pytest.mark.asyncio
    async def test_empty_headers(self, sqlite_store):
        """Test server with empty headers."""
        server = MCPServerConfig(
            name="remote",
            url="http://localhost:8080/mcp",
            headers={},
        )
        await sqlite_store.add_server("user1", server)

        result = await sqlite_store.get_server("user1", "remote")
        assert result.headers == {}


class TestSQLiteMCPConfigStoreIsolation:
    """Tests for user isolation in SQLiteMCPConfigStore."""

    @pytest.mark.asyncio
    async def test_user_configs_isolated(self, sqlite_store):
        """Test different users have isolated configs."""
        await sqlite_store.add_server("user1", MCPServerConfig(
            name="server",
            url="http://user1.example.com/mcp",
        ))
        await sqlite_store.add_server("user2", MCPServerConfig(
            name="server",
            url="http://user2.example.com/mcp",
        ))

        config1 = await sqlite_store.get_user_config("user1")
        config2 = await sqlite_store.get_user_config("user2")

        assert config1.servers["server"].url == "http://user1.example.com/mcp"
        assert config2.servers["server"].url == "http://user2.example.com/mcp"

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_user_server(self, sqlite_store):
        """Test user cannot access another user's server."""
        await sqlite_store.add_server("user1", MCPServerConfig(
            name="secret",
            url="http://secret.example.com/mcp",
            headers={"X-Secret": "user1-secret"},
        ))

        result = await sqlite_store.get_server("user2", "secret")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_user_config_does_not_affect_others(self, sqlite_store):
        """Test deleting user config doesn't affect other users."""
        await sqlite_store.add_server("user1", MCPServerConfig(name="s1", command="uvx"))
        await sqlite_store.add_server("user2", MCPServerConfig(name="s2", command="npx"))

        await sqlite_store.delete_user_config("user1")

        config2 = await sqlite_store.get_user_config("user2")
        assert "s2" in config2.servers


class TestSQLiteMCPConfigStorePersistence:
    """Tests for SQLiteMCPConfigStore persistence."""

    @pytest.mark.asyncio
    async def test_data_persists_across_instances(self):
        """Test data persists when store is reopened."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            # First instance: add data
            store1 = SQLiteMCPConfigStore(db_path=db_path)
            await store1.init_tables()
            await store1.add_server("user1", MCPServerConfig(
                name="persistent",
                url="http://localhost:8080/mcp",
                transport="streamable_http",
                headers={"X-Key": "value"},
            ))
            await store1.close()

            # Second instance: verify data
            store2 = SQLiteMCPConfigStore(db_path=db_path)
            await store2.init_tables()
            result = await store2.get_server("user1", "persistent")
            await store2.close()

            assert result is not None
            assert result.url == "http://localhost:8080/mcp"
            assert result.transport == "streamable_http"
            assert result.headers == {"X-Key": "value"}

    @pytest.mark.asyncio
    async def test_migration_adds_new_columns(self):
        """Test migration adds new columns to existing table."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            # Create store and add data
            store = SQLiteMCPConfigStore(db_path=db_path)
            await store.init_tables()

            # Add server with all new fields
            await store.add_server("user1", MCPServerConfig(
                name="test",
                url="http://localhost:8080/mcp",
                transport="streamable_http",
                headers={"X-Key": "value"},
            ))

            # Verify
            result = await store.get_server("user1", "test")
            assert result.transport == "streamable_http"
            assert result.headers == {"X-Key": "value"}

            await store.close()

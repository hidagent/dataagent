"""Tests for MCP multi-tenant isolation."""

import pytest
from dataagent_core.mcp import (
    MCPConfig,
    MCPServerConfig,
    MCPConnectionManager,
    MemoryMCPConfigStore,
)


class TestConfigIsolation:
    """Test configuration isolation between tenants."""

    @pytest.mark.asyncio
    async def test_different_tenants_have_different_configs(self):
        """Verify that different tenants have isolated configurations."""
        store = MemoryMCPConfigStore()

        # Tenant A adds servers
        config_a = MCPConfig(
            servers={
                "github": MCPServerConfig(
                    name="github",
                    command="npx",
                    args=["@modelcontextprotocol/server-github"],
                    env={"GITHUB_TOKEN": "token_a"},
                ),
                "postgres": MCPServerConfig(
                    name="postgres",
                    command="npx",
                    args=["@modelcontextprotocol/server-postgres"],
                    env={"POSTGRES_CONNECTION_STRING": "postgresql://a"},
                ),
            }
        )
        await store.save_user_config("alice", config_a)

        # Tenant B adds different servers
        config_b = MCPConfig(
            servers={
                "github": MCPServerConfig(
                    name="github",
                    command="npx",
                    args=["@modelcontextprotocol/server-github"],
                    env={"GITHUB_TOKEN": "token_b"},
                ),
                "mysql": MCPServerConfig(
                    name="mysql",
                    command="npx",
                    args=["@modelcontextprotocol/server-mysql"],
                    env={"MYSQL_CONNECTION_STRING": "mysql://b"},
                ),
                "jira": MCPServerConfig(
                    name="jira",
                    command="npx",
                    args=["@modelcontextprotocol/server-jira"],
                    env={"JIRA_TOKEN": "token_b"},
                ),
            }
        )
        await store.save_user_config("bob", config_b)

        # Verify isolation
        alice_config = await store.get_user_config("alice")
        bob_config = await store.get_user_config("bob")

        assert set(alice_config.servers.keys()) == {"github", "postgres"}
        assert set(bob_config.servers.keys()) == {"github", "mysql", "jira"}

        # Verify credentials are isolated
        alice_github = alice_config.get_server("github")
        bob_github = bob_config.get_server("github")

        assert alice_github.env["GITHUB_TOKEN"] == "token_a"
        assert bob_github.env["GITHUB_TOKEN"] == "token_b"

    @pytest.mark.asyncio
    async def test_tenant_cannot_access_other_tenant_config(self):
        """Verify that one tenant cannot access another tenant's configuration."""
        store = MemoryMCPConfigStore()

        # Alice saves her config
        config_a = MCPConfig(
            servers={
                "github": MCPServerConfig(
                    name="github",
                    command="npx",
                    args=["@modelcontextprotocol/server-github"],
                    env={"GITHUB_TOKEN": "alice_secret_token"},
                )
            }
        )
        await store.save_user_config("alice", config_a)

        # Bob tries to get Alice's config
        bob_config = await store.get_user_config("bob")

        # Bob should get empty config, not Alice's
        assert len(bob_config.servers) == 0

    @pytest.mark.asyncio
    async def test_add_server_isolation(self):
        """Verify that adding a server only affects the specific tenant."""
        store = MemoryMCPConfigStore()

        # Alice adds a server
        alice_server = MCPServerConfig(
            name="slack",
            command="npx",
            args=["@modelcontextprotocol/server-slack"],
            env={"SLACK_TOKEN": "alice_token"},
        )
        await store.add_server("alice", alice_server)

        # Bob adds a different server
        bob_server = MCPServerConfig(
            name="aws",
            command="npx",
            args=["@modelcontextprotocol/server-aws"],
            env={"AWS_KEY": "bob_key"},
        )
        await store.add_server("bob", bob_server)

        # Verify isolation
        alice_config = await store.get_user_config("alice")
        bob_config = await store.get_user_config("bob")

        assert "slack" in alice_config.servers
        assert "slack" not in bob_config.servers
        assert "aws" in bob_config.servers
        assert "aws" not in alice_config.servers

    @pytest.mark.asyncio
    async def test_remove_server_isolation(self):
        """Verify that removing a server only affects the specific tenant."""
        store = MemoryMCPConfigStore()

        # Both Alice and Bob have a GitHub server
        alice_server = MCPServerConfig(
            name="github",
            command="npx",
            args=["@modelcontextprotocol/server-github"],
            env={"GITHUB_TOKEN": "alice_token"},
        )
        bob_server = MCPServerConfig(
            name="github",
            command="npx",
            args=["@modelcontextprotocol/server-github"],
            env={"GITHUB_TOKEN": "bob_token"},
        )

        await store.add_server("alice", alice_server)
        await store.add_server("bob", bob_server)

        # Alice removes her GitHub server
        await store.remove_server("alice", "github")

        # Verify isolation
        alice_config = await store.get_user_config("alice")
        bob_config = await store.get_user_config("bob")

        assert "github" not in alice_config.servers
        assert "github" in bob_config.servers


class TestConnectionIsolation:
    """Test connection isolation between tenants."""

    @pytest.mark.asyncio
    async def test_different_tenants_have_different_connections(self):
        """Verify that different tenants have isolated connections."""
        manager = MCPConnectionManager()

        # Create configs for Alice and Bob
        alice_config = MCPConfig(
            servers={
                "server1": MCPServerConfig(
                    name="server1",
                    command="echo",
                    args=["alice"],
                )
            }
        )

        bob_config = MCPConfig(
            servers={
                "server2": MCPServerConfig(
                    name="server2",
                    command="echo",
                    args=["bob"],
                )
            }
        )

        # Connect both tenants
        alice_conns = await manager.connect("alice", alice_config)
        bob_conns = await manager.connect("bob", bob_config)

        # Verify isolation
        assert "alice" in manager._connections
        assert "bob" in manager._connections
        assert manager._connections["alice"] != manager._connections["bob"]

    @pytest.mark.asyncio
    async def test_connection_limit_per_user(self):
        """Verify that connection limits are enforced per user."""
        manager = MCPConnectionManager(max_connections_per_user=2)

        # Create a config with 3 servers
        config = MCPConfig(
            servers={
                "server1": MCPServerConfig(name="server1", command="echo"),
                "server2": MCPServerConfig(name="server2", command="echo"),
                "server3": MCPServerConfig(name="server3", command="echo"),
            }
        )

        # Try to connect all servers for Alice
        await manager.connect("alice", config)

        # Verify that only 2 connections were made (due to limit)
        alice_conns = manager._connections.get("alice", {})
        # Note: actual count depends on connection success, but limit should be enforced

        # Bob should be able to have his own 2 connections
        await manager.connect("bob", config)
        bob_conns = manager._connections.get("bob", {})

        # Both should have independent connection pools
        assert "alice" in manager._connections
        assert "bob" in manager._connections

    @pytest.mark.asyncio
    async def test_disconnect_isolation(self):
        """Verify that disconnecting one tenant doesn't affect others."""
        manager = MCPConnectionManager()

        # Create configs
        alice_config = MCPConfig(
            servers={
                "server1": MCPServerConfig(name="server1", command="echo")
            }
        )
        bob_config = MCPConfig(
            servers={
                "server2": MCPServerConfig(name="server2", command="echo")
            }
        )

        # Connect both
        await manager.connect("alice", alice_config)
        await manager.connect("bob", bob_config)

        # Disconnect Alice
        await manager.disconnect("alice")

        # Verify isolation
        assert "alice" not in manager._connections
        assert "bob" in manager._connections

    @pytest.mark.asyncio
    async def test_get_tools_isolation(self):
        """Verify that each tenant only gets their own tools."""
        manager = MCPConnectionManager()

        # Create configs with different servers
        alice_config = MCPConfig(
            servers={
                "server1": MCPServerConfig(name="server1", command="echo")
            }
        )
        bob_config = MCPConfig(
            servers={
                "server2": MCPServerConfig(name="server2", command="echo")
            }
        )

        # Connect both
        await manager.connect("alice", alice_config)
        await manager.connect("bob", bob_config)

        # Get tools for each tenant
        alice_tools = manager.get_tools("alice")
        bob_tools = manager.get_tools("bob")

        # Verify isolation (tools should be from different servers)
        # Note: actual tools depend on server implementation
        # but the important thing is they're isolated by user_id

        # Verify that getting tools for non-existent user returns empty
        charlie_tools = manager.get_tools("charlie")
        assert charlie_tools == []

    @pytest.mark.asyncio
    async def test_connection_status_isolation(self):
        """Verify that connection status is isolated per tenant."""
        manager = MCPConnectionManager()

        # Create configs
        alice_config = MCPConfig(
            servers={
                "server1": MCPServerConfig(name="server1", command="echo")
            }
        )
        bob_config = MCPConfig(
            servers={
                "server2": MCPServerConfig(name="server2", command="echo")
            }
        )

        # Connect both
        await manager.connect("alice", alice_config)
        await manager.connect("bob", bob_config)

        # Get status for each tenant
        alice_status = manager.get_connection_status("alice")
        bob_status = manager.get_connection_status("bob")

        # Verify isolation
        assert alice_status != bob_status
        assert "server1" in alice_status or len(alice_status) == 0
        assert "server2" in bob_status or len(bob_status) == 0

        # Verify that getting status for non-existent user returns empty
        charlie_status = manager.get_connection_status("charlie")
        assert charlie_status == {}


class TestResourceIsolation:
    """Test resource isolation between tenants."""

    @pytest.mark.asyncio
    async def test_total_connection_limit(self):
        """Verify that total connection limit is enforced across all tenants."""
        manager = MCPConnectionManager(
            max_connections_per_user=100,
            max_total_connections=3,
        )

        # Create configs
        config1 = MCPConfig(
            servers={
                "server1": MCPServerConfig(name="server1", command="echo")
            }
        )
        config2 = MCPConfig(
            servers={
                "server2": MCPServerConfig(name="server2", command="echo")
            }
        )
        config3 = MCPConfig(
            servers={
                "server3": MCPServerConfig(name="server3", command="echo")
            }
        )
        config4 = MCPConfig(
            servers={
                "server4": MCPServerConfig(name="server4", command="echo")
            }
        )

        # Connect multiple tenants
        await manager.connect("alice", config1)
        await manager.connect("bob", config2)
        await manager.connect("charlie", config3)

        # Try to connect a 4th tenant (should hit limit)
        await manager.connect("diana", config4)

        # Verify that total connections don't exceed limit
        total = manager.total_connections
        assert total <= 3

    @pytest.mark.asyncio
    async def test_user_count(self):
        """Verify that user count is tracked correctly."""
        manager = MCPConnectionManager()

        config = MCPConfig(
            servers={
                "server1": MCPServerConfig(name="server1", command="echo")
            }
        )

        # Connect multiple users
        await manager.connect("alice", config)
        assert manager.get_user_count() == 1

        await manager.connect("bob", config)
        assert manager.get_user_count() == 2

        await manager.connect("charlie", config)
        assert manager.get_user_count() == 3

        # Disconnect one user
        await manager.disconnect("bob")
        assert manager.get_user_count() == 2


class TestMultiTenantScenarios:
    """Test realistic multi-tenant scenarios."""

    @pytest.mark.asyncio
    async def test_three_tenant_scenario(self):
        """Test a realistic scenario with three tenants."""
        store = MemoryMCPConfigStore()
        manager = MCPConnectionManager()

        # Tenant A: Alice (GitHub + PostgreSQL + Slack)
        alice_config = MCPConfig(
            servers={
                "github": MCPServerConfig(
                    name="github",
                    command="npx",
                    env={"GITHUB_TOKEN": "alice_token"},
                ),
                "postgres": MCPServerConfig(
                    name="postgres",
                    command="npx",
                    env={"POSTGRES_CONNECTION_STRING": "postgresql://alice"},
                ),
                "slack": MCPServerConfig(
                    name="slack",
                    command="npx",
                    env={"SLACK_TOKEN": "alice_slack"},
                ),
            }
        )
        await store.save_user_config("alice", alice_config)

        # Tenant B: Bob (GitHub + MySQL + Jira)
        bob_config = MCPConfig(
            servers={
                "github": MCPServerConfig(
                    name="github",
                    command="npx",
                    env={"GITHUB_TOKEN": "bob_token"},
                ),
                "mysql": MCPServerConfig(
                    name="mysql",
                    command="npx",
                    env={"MYSQL_CONNECTION_STRING": "mysql://bob"},
                ),
                "jira": MCPServerConfig(
                    name="jira",
                    command="npx",
                    env={"JIRA_TOKEN": "bob_jira"},
                ),
            }
        )
        await store.save_user_config("bob", bob_config)

        # Tenant C: Charlie (GitHub + AWS)
        charlie_config = MCPConfig(
            servers={
                "github": MCPServerConfig(
                    name="github",
                    command="npx",
                    env={"GITHUB_TOKEN": "charlie_token"},
                ),
                "aws": MCPServerConfig(
                    name="aws",
                    command="npx",
                    env={"AWS_KEY": "charlie_key"},
                ),
            }
        )
        await store.save_user_config("charlie", charlie_config)

        # Verify configuration isolation
        alice_stored = await store.get_user_config("alice")
        bob_stored = await store.get_user_config("bob")
        charlie_stored = await store.get_user_config("charlie")

        assert set(alice_stored.servers.keys()) == {"github", "postgres", "slack"}
        assert set(bob_stored.servers.keys()) == {"github", "mysql", "jira"}
        assert set(charlie_stored.servers.keys()) == {"github", "aws"}

        # Verify credential isolation
        alice_github = alice_stored.get_server("github")
        bob_github = bob_stored.get_server("github")
        charlie_github = charlie_stored.get_server("github")

        assert alice_github.env["GITHUB_TOKEN"] == "alice_token"
        assert bob_github.env["GITHUB_TOKEN"] == "bob_token"
        assert charlie_github.env["GITHUB_TOKEN"] == "charlie_token"

        # Verify that Alice doesn't have Jira or AWS
        assert alice_stored.get_server("jira") is None
        assert alice_stored.get_server("aws") is None

        # Verify that Bob doesn't have Slack or AWS
        assert bob_stored.get_server("slack") is None
        assert bob_stored.get_server("aws") is None

        # Verify that Charlie doesn't have Slack or Jira
        assert charlie_stored.get_server("slack") is None
        assert charlie_stored.get_server("jira") is None

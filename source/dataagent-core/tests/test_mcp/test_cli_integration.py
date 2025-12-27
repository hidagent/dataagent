"""Integration tests for CLI MCP management commands.

Tests the complete command flow: add → list → show → update → disable → enable → remove
"""

import json
import tempfile
from pathlib import Path

import pytest

from dataagent_core.mcp.config import MCPServerConfig, MCPConfig
from dataagent_core.mcp.loader import MCPConfigLoader


class TestMCPCommandFlow:
    """Integration tests for the complete MCP command flow."""

    def test_full_command_flow(self):
        """Test add → list → show → update → disable → enable → remove flow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config_path.write_text('{"mcpServers": {}}')
            
            loader = MCPConfigLoader(config_path=config_path)
            
            # 1. ADD - Add a new server
            server = MCPServerConfig(
                name="test-server",
                command="uvx",
                args=["test-package"],
                env={"API_KEY": "secret"},
                disabled=False,
            )
            result = loader.add_server(server)
            assert result is True, "Add server should succeed"
            
            # 2. LIST - Verify server appears in list
            config = loader.load_config()
            assert "test-server" in config.servers
            assert len(config.servers) == 1
            
            # 3. SHOW - Get server details
            server_info = loader.get_server("test-server")
            assert server_info is not None
            assert server_info.name == "test-server"
            assert server_info.command == "uvx"
            assert server_info.args == ["test-package"]
            assert server_info.env == {"API_KEY": "secret"}
            assert server_info.disabled is False
            
            # 4. UPDATE - Modify server configuration
            result = loader.update_server(
                "test-server",
                command="npx",
                args=["updated-package"],
            )
            assert result is True, "Update server should succeed"
            
            # Verify update
            server_info = loader.get_server("test-server")
            assert server_info.command == "npx"
            assert server_info.args == ["updated-package"]
            assert server_info.env == {"API_KEY": "secret"}  # Unchanged
            
            # 5. DISABLE - Disable the server
            result = loader.set_server_disabled("test-server", True)
            assert result is True, "Disable server should succeed"
            
            server_info = loader.get_server("test-server")
            assert server_info.disabled is True
            
            # Verify disabled server not in enabled list
            config = loader.load_config()
            enabled = config.get_enabled_servers()
            assert "test-server" not in enabled
            
            # 6. ENABLE - Re-enable the server
            result = loader.set_server_disabled("test-server", False)
            assert result is True, "Enable server should succeed"
            
            server_info = loader.get_server("test-server")
            assert server_info.disabled is False
            
            # Verify enabled server in enabled list
            config = loader.reload_config()
            enabled = config.get_enabled_servers()
            assert "test-server" in enabled
            
            # 7. REMOVE - Remove the server
            result = loader.remove_server("test-server")
            assert result is True, "Remove server should succeed"
            
            # Verify removal
            assert loader.get_server("test-server") is None
            config = loader.reload_config()
            assert len(config.servers) == 0

    def test_multiple_servers_flow(self):
        """Test managing multiple servers simultaneously."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config_path.write_text('{"mcpServers": {}}')
            
            loader = MCPConfigLoader(config_path=config_path)
            
            # Add multiple servers
            servers = [
                MCPServerConfig(name="server-1", command="uvx", args=["pkg1"]),
                MCPServerConfig(name="server-2", command="npx", args=["pkg2"]),
                MCPServerConfig(name="server-3", url="http://localhost:8080"),
            ]
            
            for server in servers:
                result = loader.add_server(server)
                assert result is True
            
            # Verify all servers added
            config = loader.load_config()
            assert len(config.servers) == 3
            
            # Disable one server
            loader.set_server_disabled("server-2", True)
            
            # Verify only 2 enabled
            config = loader.reload_config()
            enabled = config.get_enabled_servers()
            assert len(enabled) == 2
            assert "server-1" in enabled
            assert "server-2" not in enabled
            assert "server-3" in enabled
            
            # Update one server
            loader.update_server("server-1", args=["updated-pkg1"])
            
            # Verify update didn't affect others
            s1 = loader.get_server("server-1")
            s2 = loader.get_server("server-2")
            s3 = loader.get_server("server-3")
            
            assert s1.args == ["updated-pkg1"]
            assert s2.args == ["pkg2"]  # Unchanged
            assert s3.url == "http://localhost:8080"  # Unchanged
            
            # Remove one server
            loader.remove_server("server-2")
            
            # Verify removal didn't affect others
            config = loader.reload_config()
            assert len(config.servers) == 2
            assert "server-1" in config.servers
            assert "server-2" not in config.servers
            assert "server-3" in config.servers

    def test_persistence_across_loader_instances(self):
        """Test that changes persist across loader instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config_path.write_text('{"mcpServers": {}}')
            
            # First loader: add server
            loader1 = MCPConfigLoader(config_path=config_path)
            loader1.add_server(MCPServerConfig(name="persistent", command="uvx"))
            
            # Second loader: verify and update
            loader2 = MCPConfigLoader(config_path=config_path)
            assert loader2.get_server("persistent") is not None
            loader2.update_server("persistent", args=["new-arg"])
            
            # Third loader: verify update and disable
            loader3 = MCPConfigLoader(config_path=config_path)
            server = loader3.get_server("persistent")
            assert server.args == ["new-arg"]
            loader3.set_server_disabled("persistent", True)
            
            # Fourth loader: verify disable and remove
            loader4 = MCPConfigLoader(config_path=config_path)
            assert loader4.get_server("persistent").disabled is True
            loader4.remove_server("persistent")
            
            # Fifth loader: verify removal
            loader5 = MCPConfigLoader(config_path=config_path)
            assert loader5.get_server("persistent") is None

    def test_error_handling_flow(self):
        """Test error handling in command flow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config_path.write_text('{"mcpServers": {}}')
            
            loader = MCPConfigLoader(config_path=config_path)
            
            # Operations on non-existent server should fail gracefully
            assert loader.get_server("nonexistent") is None
            assert loader.remove_server("nonexistent") is False
            assert loader.update_server("nonexistent", command="new") is False
            assert loader.set_server_disabled("nonexistent", True) is False
            
            # Add a server
            loader.add_server(MCPServerConfig(name="existing", command="uvx"))
            
            # Duplicate add should fail
            result = loader.add_server(MCPServerConfig(name="existing", command="npx"))
            assert result is False
            
            # Original should be unchanged
            assert loader.get_server("existing").command == "uvx"

    def test_url_server_flow(self):
        """Test flow with URL-based servers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config_path.write_text('{"mcpServers": {}}')
            
            loader = MCPConfigLoader(config_path=config_path)
            
            # Add URL server
            server = MCPServerConfig(
                name="url-server",
                url="http://localhost:8080/mcp",
                transport="streamable-http",
                headers={"Authorization": "Bearer token"},
            )
            loader.add_server(server)
            
            # Verify
            info = loader.get_server("url-server")
            assert info.url == "http://localhost:8080/mcp"
            assert info.transport == "streamable-http"
            assert info.headers == {"Authorization": "Bearer token"}
            
            # Update URL
            loader.update_server("url-server", url="http://localhost:9090/mcp")
            
            info = loader.get_server("url-server")
            assert info.url == "http://localhost:9090/mcp"
            assert info.transport == "streamable-http"  # Unchanged
